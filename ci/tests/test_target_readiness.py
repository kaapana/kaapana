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


def _apiserver(rejects=(), unreachable=False):
    """A kubectl that answers a NodePort dry-run the way the API server does."""

    def fake_run(cmd, timeout=60):
        if unreachable:
            return 1, "", "The connection to the server 127.0.0.1:16443 was refused"
        port = int([arg for arg in cmd if arg.startswith("--node-port=")][0].split("=")[1])
        if port in rejects:
            return (
                1,
                "",
                f'The Service "kaapana-node-port-probe" is invalid: '
                f"spec.ports[0].nodePort: Invalid value: {port}: provided port is not "
                "in the valid range. The range of valid ports is 30000-32767",
            )
        return 0, "service/kaapana-node-port-probe created (server dry run)", ""

    return fake_run


def test_the_node_port_range_is_read_from_the_api_server(readiness, monkeypatch):
    monkeypatch.setattr(readiness, "run", _apiserver(rejects=(80, 443)))
    report = readiness.Report()
    readiness.check_node_port_range(report, "/snap/bin/microk8s", [80, 443, 11112])
    assert report.checks[0]["status"] == readiness.FAILED
    assert "30000-32767" in report.checks[0]["details"]

    monkeypatch.setattr(readiness, "run", _apiserver())
    ok = readiness.Report()
    readiness.check_node_port_range(ok, "/snap/bin/microk8s", [80, 443, 11112])
    assert ok.checks[0]["status"] == readiness.PASSED


def test_the_node_port_probe_runs_through_microk8s_kubectl(readiness, monkeypatch):
    seen = []
    monkeypatch.setattr(readiness, "run", lambda cmd, timeout=60: (seen.append(cmd), (0, "", ""))[1])
    readiness.check_node_port_range(readiness.Report(), "/snap/bin/microk8s", [80])
    assert seen[0][:2] == ["/snap/bin/microk8s", "kubectl"]


def test_the_node_port_probe_falls_back_to_plain_kubectl(readiness, monkeypatch):
    """No kube distribution is assumed: any kubectl on PATH will do."""
    seen = []
    monkeypatch.setattr(readiness.shutil, "which", lambda name: "/usr/bin/kubectl")
    monkeypatch.setattr(readiness, "run", lambda cmd, timeout=60: (seen.append(cmd), (0, "", ""))[1])
    readiness.check_node_port_range(readiness.Report(), "", [80])
    assert seen[0][:1] == ["/usr/bin/kubectl"]


def test_an_allocated_node_port_is_inside_the_range(readiness, monkeypatch):
    """check_ports_free owns occupancy; this check only asks about the range."""
    monkeypatch.setattr(
        readiness,
        "run",
        lambda *a, **k: (1, "", "provided port is already allocated"),
    )
    report = readiness.Report()
    readiness.check_node_port_range(report, "/snap/bin/microk8s", [80])
    assert report.checks[0]["status"] == readiness.PASSED


def test_an_unanswered_node_port_probe_fails_instead_of_skipping(readiness, monkeypatch):
    """An unchecked range must not pass the gate silently."""
    monkeypatch.setattr(readiness, "run", _apiserver(unreachable=True))
    report = readiness.Report()
    readiness.check_node_port_range(report, "/snap/bin/microk8s", [80, 443, 11112])
    assert report.checks[0]["status"] == readiness.FAILED
    assert report.ready is False


def test_the_node_port_range_is_skipped_without_a_kubectl(readiness, monkeypatch):
    """Advisory run: server_installation installs the cluster and sets the range."""
    monkeypatch.setattr(readiness.shutil, "which", lambda name: None)
    report = readiness.Report(advisory=True)
    readiness.check_node_port_range(report, "", [80, 443, 11112])
    assert report.checks[0]["status"] == readiness.SKIPPED
    assert report.ready is True


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
