#!/usr/bin/env python3
"""Sweep orphaned CI test VMs on Harvester.

A test VM leaks whenever its pipeline ends without `destroy_deployment`
running for the VM that exists. A retried `prepare_deployment` is the
documented case, since GitLab never cascades retries. The pipeline id stamped
on the VM is what separates a leak from a VM a run still needs; age alone
cannot, because a run may legitimately hold a VM for hours. Age is the ripcord
for VMs that carry no pipeline at all.

Reports to stdout and as JSON, and deletes nothing without `--apply`. The
deletion itself goes through `delete_harvester_vm.yaml` so that VM and PVC
teardown keeps exactly one implementation.
"""

import argparse
import dataclasses
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PIPELINE_ID_LABEL = "kaapana.io/ci-pipeline-id"
PIPELINE_URL_ANNOTATION = "kaapana.io/ci-pipeline-url"
KEEP_ANNOTATION = "kaapana.io/ci-keep-after-pipeline"
# The CI runner VMs share this namespace and are named kaapana-*; the prefix is
# what keeps the sweep off them.
VM_NAME_PREFIX = "ci-"
DELETE_PLAYBOOK = Path(__file__).parents[1] / "deploy/delete_harvester_vm.yaml"
# Anything absent from this set counts as alive: an unknown or newly introduced
# GitLab state must never authorize a deletion. A pipeline blocked on a delayed
# destroy_deployment (CI_EXEC_DESTROY_DELAYED) is non-terminal, which is
# precisely why that case needs no rule of its own.
TERMINAL_PIPELINE_STATES = frozenset({"success", "failed", "canceled", "skipped"})

REQUIRED_ENV = [
    "HARVESTER_KUBECONFIG",
    "DEPLOYMENT_INSTANCE_HARVESTER_NAMESPACE",
    # The job's own token, not GITLAB_API_TOKEN: that one aliases the registry
    # credential, which the REST API answers with 401.
    "CI_JOB_TOKEN",
    "CI_PROJECT_ID",
    "CI_SERVER_URL",
]


@dataclasses.dataclass(frozen=True)
class Candidate:
    """A VM as the sweep sees it, with the pipeline already resolved."""

    name: str
    age_hours: float
    pipeline_id: str = ""
    pipeline_url: str = ""
    # None means "no pipeline to ask": unlabelled VM, or a pipeline GitLab no
    # longer knows. Both fall back to the age ripcord.
    pipeline_state: str | None = None
    # The run asked for this VM to survive its pipeline, for inspection.
    keep_after_pipeline: bool = False
    # None while the pipeline has not finished.
    hours_since_pipeline_end: float | None = None


def decide(
    candidate: Candidate,
    grace_hours: float,
    max_age_hours: float,
    keep_hours: float = 0.0,
) -> tuple[str, str]:
    """Return ("keep"|"delete", reason) for one VM."""
    if not candidate.name.startswith(VM_NAME_PREFIX):
        return "keep", f"not a test VM: name lacks the {VM_NAME_PREFIX!r} prefix"

    if candidate.age_hours < grace_hours:
        return "keep", f"younger than the {grace_hours:g}h grace period"

    if candidate.pipeline_state in TERMINAL_PIPELINE_STATES:
        held_for = candidate.hours_since_pipeline_end
        if candidate.keep_after_pipeline and (held_for or 0) < keep_hours:
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
    return "keep", f"{unowned} but is below the {max_age_hours:g}h age ripcord"


def hours_since(timestamp: str, now: datetime) -> float:
    return (now - datetime.fromisoformat(timestamp)).total_seconds() / 3600


# The two I/O functions import their client locally, so the decision logic
# above stays importable, and testable, without a cluster or GitLab.
def list_vms(kubeconfig: str, namespace: str) -> list[dict]:
    from kubernetes import client, config

    config.load_kube_config(config_file=kubeconfig)
    return client.CustomObjectsApi().list_namespaced_custom_object(
        group="kubevirt.io",
        version="v1",
        namespace=namespace,
        plural="virtualmachines",
    )["items"]


def gitlab_project(server_url: str, project_id: str, job_token: str):
    """Return the project, having proven that pipelines can be read.

    A credential the API refuses would make every labelled VM look unowned,
    and the age ripcord would then sweep VMs of running pipelines. The proof
    therefore happens before a single VM is looked at, and it reads a pipeline
    rather than just authenticating, because that is the right the sweep needs.
    """
    import gitlab

    project = gitlab.Gitlab(url=server_url, job_token=job_token).projects.get(
        project_id, lazy=True
    )
    project.pipelines.list(per_page=1, get_all=False)
    return project


def pipeline_facts(project, pipeline_id: str) -> tuple[str, str] | None:
    """Return (status, finished_at), or None if GitLab knows no such pipeline.

    finished_at is empty while the pipeline still runs, which is why the caller
    must not read it as "ended just now".
    """
    import gitlab

    try:
        pipeline = project.pipelines.get(int(pipeline_id))
    except (gitlab.exceptions.GitlabGetError, ValueError):
        return None
    return pipeline.status, pipeline.finished_at or ""


def delete_vm(vm_name: str) -> None:
    """Hand the VM to the teardown playbook.

    It derives the name from VM_FQDN's first label, so a bare name passes
    through unchanged.
    """
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
                pipeline_url=annotations.get(PIPELINE_URL_ANNOTATION, ""),
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
    parser.add_argument("--report", type=Path, help="write the JSON report here")
    args = parser.parse_args()

    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        # Without GitLab access every labelled VM would look unowned and the
        # age ripcord would sweep live runs, so this is a precondition.
        print(f"ERROR: missing environment variables: {', '.join(missing)}")
        return 1

    import gitlab

    namespace = os.environ["DEPLOYMENT_INSTANCE_HARVESTER_NAMESPACE"]
    try:
        project = gitlab_project(
            os.environ["CI_SERVER_URL"],
            os.environ["CI_PROJECT_ID"],
            os.environ["CI_JOB_TOKEN"],
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
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Report written to {args.report}")

    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
