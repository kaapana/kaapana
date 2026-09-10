"""The target readiness check

No GitLab, no SSH, no microk8s: the checks are driven through monkeypatched
system calls, so this is the layer that runs anywhere.
"""

import json

import pytest


@pytest.fixture
def report(readiness):
    return readiness.Report(target="host.dkfz.de")


def test_a_failed_warning_check_is_only_a_warning(report, readiness):
    report.add("x", "X", readiness.FAILED, readiness.WARNING, details="d", remediation="fix")
    assert report.checks[0]["status"] == readiness.WARNED
    assert report.ready is True


def test_a_failed_fatal_check_blocks_the_deployment(report, readiness):
    report.add("x", "X", readiness.FAILED, readiness.FATAL)
    assert report.ready is False
    assert report.verdict == "not_ready"


def test_a_passing_check_carries_no_remediation(report, readiness):
    report.add("x", "X", readiness.PASSED, readiness.FATAL, remediation="fix")
    assert report.checks[0]["remediation"] == ""


def test_advisory_demotes_what_the_installation_fixes(readiness):
    """server_installation runs next and installs what is missing, so a
    missing microk8s must not fail the pipeline."""
    report = readiness.Report(advisory=True, target="host.dkfz.de")
    report.add("microk8s", "microk8s is installed", readiness.FAILED, readiness.FATAL)
    assert report.checks[0]["status"] == readiness.WARNED
    assert report.ready is True
    assert report.verdict == "advisory"


def test_advisory_keeps_an_exempt_failure_fatal(readiness):
    """Not everything is the installer's to fix; those rows still block."""
    report = readiness.Report(advisory=True)
    report.add("x", "X", readiness.FAILED, readiness.FATAL, advisory_exempt=True)
    assert report.checks[0]["status"] == readiness.FAILED
    assert report.ready is False
    assert report.verdict == "not_ready"
    assert "TARGET NOT READY" in report.table()


def test_failures_come_first_in_the_table(report, readiness):
    report.add("ok", "Passing check", readiness.PASSED, readiness.FATAL)
    report.add("bad", "Failing check", readiness.FAILED, readiness.FATAL)
    lines = report.table().splitlines()
    position = {
        title: next(i for i, line in enumerate(lines) if title in line) for title in ("Failing check", "Passing check")
    }
    assert position["Failing check"] < position["Passing check"]


def test_the_remediation_is_printed_under_its_row(report, readiness):
    report.add("bad", "Failing", readiness.FAILED, readiness.FATAL, remediation="do this")
    assert "-> do this" in report.table()


def test_the_json_artifact_carries_every_check(report, readiness):
    report.add("ok", "Passing", readiness.PASSED, readiness.FATAL)
    report.add("bad", "Failing", readiness.FAILED, readiness.FATAL, remediation="do this")
    payload = json.loads(json.dumps(report.to_dict()))
    assert payload["target"] == "host.dkfz.de"
    assert payload["verdict"] == "not_ready"
    assert payload["summary"] == {"passed": 1, "warnings": 0, "failed": 1, "skipped": 0}
    assert [c["name"] for c in payload["checks"]] == ["ok", "bad"]
    assert payload["checks"][1]["remediation"] == "do this"


def test_the_microk8s_group_must_be_active_in_this_session(readiness, monkeypatch):
    """Being listed in /etc/group is not enough: the SSH session must already
    carry the gid, otherwise every microk8s call needs sudo."""

    class Group:
        gr_gid = 999
        gr_mem = ["ci-user"]

    monkeypatch.setattr(readiness.grp, "getgrnam", lambda name: Group())
    monkeypatch.setattr(readiness.getpass, "getuser", lambda: "ci-user")
    monkeypatch.setattr(readiness.os, "getgroups", lambda: [100])
    report = readiness.Report()
    readiness.check_microk8s_group(report)
    check = report.checks[0]
    assert check["status"] == readiness.WARNED  # listed, so not fatal
    assert "not in this SSH session" in check["details"]


def test_a_missing_microk8s_group_is_fatal(readiness, monkeypatch):
    monkeypatch.setattr(readiness.grp, "getgrnam", lambda name: (_ for _ in ()).throw(KeyError(name)))
    report = readiness.Report()
    readiness.check_microk8s_group(report)
    assert report.checks[0]["status"] == readiness.FAILED
    assert "exec_server_installation:true" in report.checks[0]["remediation"]


def test_busy_ports_are_only_a_warning_when_our_own_platform_holds_them(readiness, monkeypatch):
    monkeypatch.setattr(readiness, "listening_ports", lambda: {80: "0.0.0.0:80"})
    report = readiness.Report()
    readiness.check_ports_free(report, [80, 443], existing_platform="kaapana-admin-chart")
    assert report.checks[0]["status"] == readiness.WARNED

    other = readiness.Report()
    readiness.check_ports_free(other, [80, 443], existing_platform=None)
    assert other.checks[0]["status"] == readiness.FAILED


def test_the_node_port_range_must_cover_the_platform_ports(readiness, monkeypatch, tmp_path):
    args = tmp_path / "kube-apiserver"
    args.write_text("--service-node-port-range=30000-32767\n")
    monkeypatch.setattr(readiness, "MICROK8S_APISERVER_ARGS", str(args))
    report = readiness.Report()
    readiness.check_node_port_range(report, [80, 443, 11112])
    assert report.checks[0]["status"] == readiness.FAILED

    args.write_text("--service-node-port-range=80-32000\n")
    ok = readiness.Report()
    readiness.check_node_port_range(ok, [80, 443, 11112])
    assert ok.checks[0]["status"] == readiness.PASSED


@pytest.mark.parametrize(
    "redeploy,advisory,status,ready,verdict",
    [
        pytest.param(False, False, "failed", False, "not_ready", id="prepared-target"),
        pytest.param(False, True, "failed", False, "not_ready", id="prepared-target+install"),
        pytest.param(True, False, "warning", True, "ready", id="redeploy"),
        pytest.param(True, True, "warning", True, "advisory", id="redeploy+install"),
    ],
)
def test_existing_platform_status_per_mode(readiness, monkeypatch, redeploy, advisory, status, ready, verdict):
    """server_installation does not undeploy anything, so a platform already
    deployed on the target blocks the run whether or not the install follows;
    exec_redeploy:true undeploys it first and holds under advisory."""
    values = json.dumps({"global": {"platform_prefix": "ci-dep"}})
    monkeypatch.setattr(readiness, "run", lambda *a, **k: (0, values, ""))
    report = readiness.Report(advisory=advisory)
    prefix = readiness.check_existing_platform(
        report,
        "/usr/bin/helm",
        redeploy=redeploy,
        admin_chart="kaapana-admin-chart",
        helm_namespace="default",
    )
    assert prefix == "ci-dep"
    assert report.checks[0]["status"] == status
    assert report.ready is ready
    assert report.verdict == verdict


def test_no_existing_platform_passes(readiness, monkeypatch):
    monkeypatch.setattr(readiness, "run", lambda *a, **k: (1, "", "release: not found"))
    report = readiness.Report()
    assert (
        readiness.check_existing_platform(
            report,
            "/usr/bin/helm",
            redeploy=False,
            admin_chart="kaapana-admin-chart",
            helm_namespace="default",
        )
        is None
    )
    assert report.checks[0]["status"] == readiness.PASSED


def test_helm_values_of_null_do_not_crash_the_check(readiness, monkeypatch):
    """helm prints a literal 'null' for a release with no user-supplied values."""
    monkeypatch.setattr(readiness, "run", lambda *a, **k: (0, "null", ""))
    report = readiness.Report()
    prefix = readiness.check_existing_platform(
        report,
        "/usr/bin/helm",
        redeploy=False,
        admin_chart="kaapana-admin-chart",
        helm_namespace="default",
    )
    assert prefix == "kaapana-admin-chart"
    assert "unknown" in report.checks[0]["details"]
