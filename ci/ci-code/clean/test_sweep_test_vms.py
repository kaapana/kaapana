# Pure-python unit test for the sweep's decision logic, runs without a cluster
# and without GitLab:
#   python -m pytest ci/ci-code/clean/test_sweep_test_vms.py
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

import sweep_test_vms as sweep

CI_DIR = Path(__file__).parents[2]
NOW = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
GRACE, MAX_AGE, KEEP = 1.0, 12.0, 4.0


def candidate(**overrides) -> sweep.Candidate:
    return sweep.Candidate(
        **{"name": "ci-develop-abc1234", "age_hours": 2.0, **overrides}
    )


def decide(**overrides) -> tuple[str, str]:
    return sweep.decide(candidate(**overrides), GRACE, MAX_AGE, KEEP)


def test_the_ci_runner_vms_are_never_swept():
    """They share the namespace with the test VMs, so this is the hard border."""
    inventory = yaml.safe_load((CI_DIR / "harvester/inventory.yaml").read_text())
    runner_names = [
        host["vm_name"]
        for group in inventory["all"]["children"].values()
        for host in group["hosts"].values()
    ]
    assert runner_names, "inventory yielded no runner VMs, the guard is untested"
    for name in runner_names:
        # Ancient and with no pipeline to vouch for it: the worst case.
        action, reason = decide(name=name, age_hours=10_000)
        assert action == "keep", f"{name}: {reason}"


@pytest.mark.parametrize("state", ["success", "failed", "canceled", "skipped"])
def test_a_settled_pipeline_releases_its_vm(state):
    action, reason = decide(pipeline_id="819338", pipeline_state=state)
    assert action == "delete"
    assert state in reason


@pytest.mark.parametrize(
    "state",
    [
        "created",
        "waiting_for_resource",
        "preparing",
        "pending",
        "running",
        "manual",
        # What a delayed destroy_deployment leaves the pipeline in.
        "scheduled",
        "canceling",
        # A state GitLab has yet to invent must not authorize a deletion.
        "some_future_state",
    ],
)
def test_a_pipeline_that_is_not_settled_keeps_its_vm(state):
    action, _ = decide(pipeline_id="819338", pipeline_state=state, age_hours=48)
    assert action == "keep"


def test_the_grace_period_outranks_a_settled_pipeline():
    action, reason = decide(
        pipeline_id="819338", pipeline_state="success", age_hours=0.5
    )
    assert action == "keep"
    assert "grace" in reason


def test_an_unlabelled_vm_falls_back_to_age():
    assert decide(age_hours=MAX_AGE + 1)[0] == "delete"
    assert decide(age_hours=MAX_AGE - 1)[0] == "keep"


def test_a_vanished_pipeline_falls_back_to_age():
    action, reason = decide(pipeline_id="819338", age_hours=MAX_AGE + 1)
    assert action == "delete"
    assert "819338" in reason


def test_age_comes_from_the_kubernetes_timestamp():
    assert sweep.hours_since("2026-09-02T09:30:00Z", NOW) == pytest.approx(2.5)


def test_a_vm_kept_for_inspection_survives_its_pipeline():
    """What CI_EXEC_DESTROY_DELAYED asks for. The sweep must not undo it just
    because the pipeline is over."""
    action, reason = decide(
        pipeline_id="819370",
        pipeline_state="failed",
        keep_after_pipeline=True,
        hours_since_pipeline_end=KEEP - 1,
        age_hours=48,
    )
    assert action == "keep"
    assert "held for inspection" in reason


def test_the_keep_window_ends():
    assert (
        decide(
            pipeline_id="819370",
            pipeline_state="failed",
            keep_after_pipeline=True,
            hours_since_pipeline_end=KEEP + 1,
        )[0]
        == "delete"
    )


def test_without_the_annotation_a_settled_pipeline_releases_at_once():
    assert (
        decide(
            pipeline_id="819370",
            pipeline_state="failed",
            hours_since_pipeline_end=0.0,
        )[0]
        == "delete"
    )


def test_collect_reads_the_pipeline_identity(monkeypatch):
    monkeypatch.setattr(
        sweep,
        "list_vms",
        lambda *_: [
            {
                "metadata": {
                    "name": "ci-develop-abc1234",
                    "creationTimestamp": "2026-09-02T09:00:00Z",
                    "labels": {sweep.PIPELINE_ID_LABEL: "819338"},
                    "annotations": {
                        sweep.PIPELINE_URL_ANNOTATION: "https://gitlab/p/1",
                        sweep.KEEP_ANNOTATION: "true",
                    },
                }
            },
            {
                "metadata": {
                    "name": "ci-old",
                    "creationTimestamp": "2026-08-01T09:00:00Z",
                }
            },
        ],
    )
    monkeypatch.setattr(
        sweep,
        "pipeline_facts",
        lambda project, pipeline_id: ("failed", "2026-09-02T11:00:00Z"),
    )

    labelled, unlabelled = sweep.collect("kubeconfig", "kaapana-ci", None, NOW)

    assert (labelled.pipeline_id, labelled.pipeline_state) == ("819338", "failed")
    assert labelled.pipeline_url == "https://gitlab/p/1"
    assert labelled.age_hours == pytest.approx(3.0)
    assert labelled.keep_after_pipeline is True
    assert labelled.hours_since_pipeline_end == pytest.approx(1.0)
    # No label means GitLab is never asked, so the state stays unknown.
    assert (unlabelled.pipeline_id, unlabelled.pipeline_state) == ("", None)


def test_the_vm_template_stamps_what_the_sweep_reads():
    """Template and sweep are the two halves of one contract."""
    template = (CI_DIR / "ci-code/deploy/templates/vm.yml.j2").read_text()
    assert sweep.PIPELINE_ID_LABEL in template
    assert sweep.PIPELINE_URL_ANNOTATION in template
    assert sweep.KEEP_ANNOTATION in template
