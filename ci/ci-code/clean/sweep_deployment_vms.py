#!/usr/bin/env python3
"""Delete CI deployment VMs whose pipeline has finished.

A retried `prepare_deployment` creates a second VM, and GitLab does not run
`destroy_deployment` again for it, so that VM is never cleaned up.

The VM carries the id of the pipeline that created it. This script asks GitLab
whether that pipeline is over. Age alone cannot tell, because a pipeline may
need its VM for hours.

Reports by default, deletes only with --apply, and leaves the deleting itself
to delete_harvester_vm.yaml.
"""

import argparse
import dataclasses
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import gitlab
from kubernetes import client, config

PIPELINE_ID_LABEL = "kaapana.io/ci-pipeline-id"
KEEP_ANNOTATION = "kaapana.io/ci-keep-after-pipeline"
# The runner VMs share this namespace, but they are named kaapana-*, not after
# a branch; the prefix is what keeps the sweep off them.
VM_NAME_PREFIX = "ci-"
DELETE_PLAYBOOK = Path(__file__).parents[1] / "deploy/delete_harvester_vm.yaml"
# Anything absent from this set counts as alive: an unknown or newly introduced
# GitLab state must never authorize a deletion.
TERMINAL_PIPELINE_STATES = frozenset({"success", "failed", "canceled", "skipped"})

REQUIRED_ENV = [
    "HARVESTER_KUBECONFIG",
    "DEPLOYMENT_INSTANCE_HARVESTER_NAMESPACE",
    # Its own credential: a job token may only PUT pipeline metadata, and
    # GITLAB_API_TOKEN aliases the registry credential, which the API rejects.
    "GITLAB_READ_API_TOKEN",
    "CI_PROJECT_ID",
    "CI_SERVER_URL",
]


@dataclasses.dataclass(frozen=True)
class Candidate:
    """A VM as the sweep sees it, with the pipeline already resolved."""

    name: str
    age_hours: float
    pipeline_id: str = ""
    # None means there is no pipeline to ask: unlabelled VM, or one GitLab no
    # longer knows. Both fall back to the age limit.
    pipeline_state: str | None = None
    keep_after_pipeline: bool = False
    # None while the pipeline has not finished.
    hours_since_pipeline_end: float | None = None


def decide(
    candidate: Candidate,
    grace_hours: float,
    max_age_hours: float,
    keep_hours: float,
) -> tuple[str, str]:
    """Return ("keep"|"delete", reason) for one VM."""
    if not candidate.name.startswith(VM_NAME_PREFIX):
        return "keep", f"not a deployment VM: name lacks the {VM_NAME_PREFIX!r} prefix"

    if candidate.age_hours < grace_hours:
        return "keep", f"younger than the {grace_hours:g}h grace period"

    if candidate.pipeline_state in TERMINAL_PIPELINE_STATES:
        held_for = candidate.hours_since_pipeline_end
        if held_for is None:
            # GitLab does not report finished_at for every terminal pipeline
            held_for = candidate.age_hours

        if candidate.keep_after_pipeline and held_for < keep_hours:
            return (
                "keep",
                f"pipeline {candidate.pipeline_id} is {candidate.pipeline_state}, "
                f"but the VM is held for inspection until {keep_hours:g}h past it",
            )
        return (
            "delete",
            f"pipeline {candidate.pipeline_id} is {candidate.pipeline_state}",
        )

    if candidate.pipeline_state is not None:
        return (
            "keep",
            f"pipeline {candidate.pipeline_id} is {candidate.pipeline_state}",
        )

    unowned = (
        f"pipeline {candidate.pipeline_id} is unknown to GitLab"
        if candidate.pipeline_id
        else "carries no pipeline label"
    )
    if candidate.age_hours >= max_age_hours:
        return "delete", f"{unowned} and is older than {max_age_hours:g}h"
    return "keep", f"{unowned} but is below the {max_age_hours:g}h age limit"


def hours_since(timestamp: str, now: datetime) -> float:
    return (now - datetime.fromisoformat(timestamp)).total_seconds() / 3600


def list_vms(kubeconfig: str, namespace: str) -> list[dict]:
    config.load_kube_config(config_file=kubeconfig)
    return client.CustomObjectsApi().list_namespaced_custom_object(
        group="kubevirt.io",
        version="v1",
        namespace=namespace,
        plural="virtualmachines",
    )["items"]


def gitlab_project(server_url: str, project_id: str, api_token: str):
    """Return the project, having proven that pipelines can be read.

    A credential the API refuses would make every labelled VM look unowned, and
    the age limit would then sweep VMs of running pipelines. So this reads a
    pipeline, not just an endpoint, before any VM is looked at.
    """
    project = gitlab.Gitlab(url=server_url, private_token=api_token).projects.get(
        project_id, lazy=True
    )
    project.pipelines.list(per_page=1, get_all=False)
    return project


def pipeline_facts(project, pipeline_id: str) -> tuple[str, str] | None:
    """Return (status, finished_at), or None if GitLab knows no such pipeline.

    finished_at is empty while the pipeline still runs.
    """
    try:
        pipeline = project.pipelines.get(int(pipeline_id))
    except (gitlab.exceptions.GitlabGetError, ValueError):
        return None
    return pipeline.status, pipeline.finished_at or ""


def delete_vm(vm_name: str) -> None:
    """Hand the VM to the teardown playbook, which reads VM_FQDN."""
    subprocess.run(
        ["ansible-playbook", "-i", "localhost,", str(DELETE_PLAYBOOK)],
        env={**os.environ, "VM_FQDN": vm_name},
        check=True,
    )


def collect(kubeconfig: str, namespace: str, project, now: datetime) -> list[Candidate]:
    candidates = []
    for vm in list_vms(kubeconfig, namespace):
        metadata = vm["metadata"]
        annotations = metadata.get("annotations", {})
        pipeline_id = metadata.get("labels", {}).get(PIPELINE_ID_LABEL, "")
        facts = pipeline_facts(project, pipeline_id) if pipeline_id else None
        state, finished_at = facts if facts else (None, "")
        candidates.append(
            Candidate(
                name=metadata["name"],
                age_hours=hours_since(metadata["creationTimestamp"], now),
                pipeline_id=pipeline_id,
                pipeline_state=state,
                keep_after_pipeline=annotations.get(KEEP_ANNOTATION, "") == "true",
                hours_since_pipeline_end=(
                    hours_since(finished_at, now) if finished_at else None
                ),
            )
        )
    return candidates


def format_report(report: dict) -> str:
    summary = report["summary"]
    mode = "apply" if report["applied"] else "dry run"
    lines = [
        f"VM sweep in {report['namespace']} ({mode}): "
        f"{summary['total']} VMs, {summary['deleted']} deleted, "
        f"{summary['kept']} kept, {summary['failed']} failed",
    ]
    for vm in report["vms"]:
        marker = {"deleted": "-", "failed": "!", "kept": " "}[vm["outcome"]]
        lines.append(
            f"  {marker} {vm['name']} ({vm['age_hours']:.1f}h): "
            f"{vm['action']}, {vm['reason']}"
            + (f" [{vm['error']}]" if vm["error"] else "")
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually delete; without it the sweep only reports",
    )
    parser.add_argument("--grace-hours", type=float, default=1.0)
    parser.add_argument("--max-age-hours", type=float, default=12.0)
    parser.add_argument(
        "--keep-hours",
        type=float,
        default=4.0,
        help="how long a VM asking to be kept survives past its pipeline",
    )
    args = parser.parse_args()

    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        # Without GitLab every labelled VM would look unowned, and the age
        # limit would then sweep live runs.
        print(f"ERROR: missing environment variables: {', '.join(missing)}")
        return 1

    namespace = os.environ["DEPLOYMENT_INSTANCE_HARVESTER_NAMESPACE"]
    try:
        project = gitlab_project(
            os.environ["CI_SERVER_URL"],
            os.environ["CI_PROJECT_ID"],
            os.environ["GITLAB_READ_API_TOKEN"],
        )
    except gitlab.exceptions.GitlabError as error:
        print(
            f"ERROR: GitLab will not answer for pipelines: {error}. Without a "
            "pipeline status the sweep cannot tell a leaked VM from one a run "
            "still needs, so it touched nothing."
        )
        return 1

    now = datetime.now(timezone.utc)
    candidates = collect(os.environ["HARVESTER_KUBECONFIG"], namespace, project, now)

    vms: list[dict] = []
    for candidate in candidates:
        action, reason = decide(
            candidate, args.grace_hours, args.max_age_hours, args.keep_hours
        )
        entry = {**dataclasses.asdict(candidate), "action": action, "reason": reason}
        entry["outcome"] = "kept"
        entry["error"] = None
        if action == "delete" and args.apply:
            try:
                delete_vm(candidate.name)
                entry["outcome"] = "deleted"
            except subprocess.CalledProcessError as error:
                entry["outcome"] = "failed"
                entry["error"] = f"teardown playbook exited {error.returncode}"
        vms.append(entry)

    outcomes = [vm["outcome"] for vm in vms]
    report = {
        "generated_at": now.isoformat(),
        "namespace": namespace,
        "applied": args.apply,
        "grace_hours": args.grace_hours,
        "max_age_hours": args.max_age_hours,
        "keep_hours": args.keep_hours,
        "summary": {
            "total": len(vms),
            "deleted": outcomes.count("deleted"),
            "kept": outcomes.count("kept"),
            "failed": outcomes.count("failed"),
            "would_delete": sum(
                1 for vm in vms if vm["action"] == "delete" and vm["outcome"] == "kept"
            ),
        },
        "vms": vms,
    }

    print(format_report(report))

    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
