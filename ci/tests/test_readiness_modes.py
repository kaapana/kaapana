"""The four shapes a deployment onto a given target can take.

`exec_redeploy` and `exec_server_installation` are independent knobs, and each
decides for a different class of failure whether it stops the run:

| exec_redeploy | exec_server_installation | platform already there | microk8s/helm missing |
|---------------|--------------------------|------------------------|-----------------------|
| true          | false                    | not fatal              | fatal                 |
| true          | true                     | not fatal              | not fatal             |
| false         | false                    | fatal                  | fatal                 |
| false         | true                     | fatal                  | not fatal             |

platform_deployment undeploys what is there when exec_redeploy is on, and
server_installation installs what is missing when exec_server_installation is
on. Neither does the other's job, which is why the two columns differ.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

# One row per mode: what each class of failure does to the run.
MODES = [
    pytest.param(True, False, False, True, 1, id="redeploy+prepared-target"),
    pytest.param(True, True, False, False, 0, id="redeploy+install"),
    pytest.param(False, False, True, True, 1, id="prepared-target"),
    pytest.param(False, True, True, False, 1, id="install"),
]


@pytest.mark.parametrize("redeploy,install,platform_fatal,server_fatal,exit_code", MODES)
def test_the_mode_matrix(redeploy, install, platform_fatal, server_fatal, exit_code, monkeypatch, readiness):
    """Both failures in one report, which is what a real run hits: a target
    that carries a platform and has nothing installed."""
    monkeypatch.setattr(readiness.shutil, "which", lambda binary: None)
    monkeypatch.setattr(
        readiness, "run", lambda *a, **k: (0, json.dumps({"global": {"platform_prefix": "ci-dep"}}), "")
    )
    report = readiness.Report(advisory=install, target="host.dkfz.de")
    readiness.check_existing_platform(
        report, "/usr/bin/helm", redeploy=redeploy, admin_chart="kaapana-admin-chart", helm_namespace="default"
    )
    readiness.check_binary(report, "microk8s_installed", "microk8s", "install it")

    status = {check["name"]: check["status"] for check in report.checks}
    assert (status["existing_platform"] == readiness.FAILED) is platform_fatal
    assert (status["microk8s_installed"] == readiness.FAILED) is server_fatal
    # rc 1 is what stops the deployment.
    assert (0 if report.ready else 1) == exit_code


PLAYBOOK = Path(__file__).resolve().parents[1] / "ci-code" / "deploy" / "target_readiness.yaml"


def readiness_play():
    return yaml.safe_load(PLAYBOOK.read_text())[0]


def test_the_playbook_reads_every_knob_from_the_environment():
    """These are CI/CD variables, so the playbook is the only place they can
    enter the check."""
    variables = readiness_play()["vars"]
    expected = {
        "vm_fqdn": "VM_FQDN",
        "redeploy": "CI_EXEC_REDEPLOY",
        "advisory": "CI_EXEC_SERVER_INSTALLATION",
        "admin_chart": "DEPLOYMENT_INSTANCE_ADMIN_CHART",
        "helm_namespace": "DEPLOYMENT_INSTANCE_HELM_NAMESPACE",
    }
    for name, env_var in expected.items():
        assert env_var in variables[name], f"{name} no longer reads {env_var}"


def test_the_playbook_passes_the_knobs_to_the_check():
    """A flag dropped here turns a fatal check back into a default."""
    task = next(
        task
        for task in readiness_play()["tasks"]
        if "ansible.builtin.script" in task and "target_readiness.py" in task["ansible.builtin.script"]["cmd"]
    )
    command = " ".join(task["ansible.builtin.script"]["cmd"].split())
    for flag, variable in (
        ("--domain", "vm_fqdn"),
        ("--redeploy", "redeploy"),
        ("--admin-chart", "admin_chart"),
        ("--helm-namespace", "helm_namespace"),
    ):
        assert re.search(rf"{flag} \{{\{{ *{variable}\b", command), f"{flag} does not pass {variable}"
    # --advisory is conditional: it is the flag that turns failures into rows.
    assert re.search(r"'--advisory' if advisory", command)


def test_the_platform_lookup_uses_the_configured_release():
    """The playbook's own helm call must look where the deployment deploys."""
    task = next(
        task for task in readiness_play()["tasks"] if task["name"] == "Read the platform already deployed on the target"
    )
    command = task["ansible.builtin.shell"]["cmd"]
    assert "{{ helm_namespace }}" in command
    assert "{{ admin_chart | quote }}" in command


def test_the_command_line_reaches_the_helm_lookup(monkeypatch, tmp_path, readiness):
    """End to end through main(): the flag the playbook passes has to arrive at
    the helm call, not just at the function that could take it."""
    commands = []

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        if "ls" in cmd:
            return 0, "[]", ""
        return 0, json.dumps({"global": {"platform_prefix": "ci-dep"}}), ""

    monkeypatch.setattr(readiness, "run", fake_run)
    monkeypatch.setattr(readiness.shutil, "which", lambda binary: f"/snap/bin/{binary}")
    monkeypatch.setattr(
        readiness.sys,
        "argv",
        [
            "target_readiness.py",
            "--domain",
            "",
            "--redeploy",
            "false",
            "--admin-chart",
            "kaapana-admin-chart-fork",
            "--helm-namespace",
            "kaapana",
            "--json",
            str(tmp_path / "report.json"),
        ],
    )
    readiness.main()
    lookup = next(cmd for cmd in commands if "get" in cmd and "values" in cmd)
    assert "kaapana-admin-chart-fork" in lookup
    assert lookup[lookup.index("-n") + 1] == "kaapana"
