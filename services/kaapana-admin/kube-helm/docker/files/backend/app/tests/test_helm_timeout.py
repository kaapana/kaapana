"""helm installs and platform deletes get their time limit as helm's --timeout and
are killed only when hung, as a kill at the limit stranded releases (kaapana#2497);
tested with a fake helm only."""

import logging
import shlex
import subprocess
import sys
import time
import types

import pytest


def _stub(monkeypatch, name, **attrs):
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    monkeypatch.setitem(sys.modules, name, module)
    return module


@pytest.fixture
def utils(monkeypatch):
    # app.config.Settings refuses to load without these.
    for name in (
        "SECRET_KEY",
        "APPLICATION_ROOT",
        "HELM_EXTENSIONS_CACHE",
        "HELM_PLATFORMS_CACHE",
        "KAAPANA_COLLECTIONS",
        "HELM_NAMESPACE",
        "RELEASE_NAME",
        "REGISTRY_URL",
        "KUBECTL_PATH",
        "HELM_PATH",
        "CONTAINERD_SOCK",
    ):
        monkeypatch.setenv(name, "unused")
    # app.utils imports kaapanapy and distutils (gone since Python 3.12), which a
    # plain development venv may lack.
    try:
        import kaapanapy.logger  # noqa: F401
    except ImportError:
        logger = _stub(monkeypatch, "kaapanapy.logger", get_logger=logging.getLogger)
        _stub(monkeypatch, "kaapanapy", logger=logger)
    try:
        import distutils.version  # noqa: F401
    except ImportError:
        version = _stub(monkeypatch, "distutils.version", LooseVersion=str)
        _stub(monkeypatch, "distutils", version=version)
    from app import utils

    return utils


@pytest.fixture
def fake_helm(tmp_path):
    """Writes a helm stand-in that logs its arguments, sleeps and prints a release."""

    def make(seconds=0):
        calls = tmp_path / "calls"
        helm = tmp_path / "helm"
        helm.write_text(
            f'#!/bin/sh\necho "$*" >> {shlex.quote(str(calls))}\n'
            f"sleep {seconds}\necho '{{}}'\n"
        )
        helm.chmod(0o755)
        return shlex.quote(str(helm)), calls

    return make


def _install(utils, command, platforms=False):
    preflight = {
        "should_install": True,
        "install_action": "install",
        "install_message": "",
        "keywords": [],
        "release_name": "r",
        "helm_command": command,
        "helm_namespace": "ns",
        "status_name": "",
    }
    return utils.helm_install(
        {"name": "r", "version": "1"},
        preflight=preflight,
        platforms=platforms,
        update_state=False,
    )


def test_install_running_past_the_limit_is_not_killed(utils, fake_helm, monkeypatch):
    monkeypatch.setattr(utils.timeouts, "helm_install_timeout", 1)
    helm, calls = fake_helm(seconds=2)

    success, *_ = _install(utils, f"{helm} -n ns install r chart.tgz -o json")

    assert success
    assert calls.read_text().split() == [
        "-n", "ns", "install", "--timeout", "1s", "r", "chart.tgz", "-o", "json"
    ]  # fmt: skip


def test_platform_install_gets_the_platform_limit(utils, fake_helm, monkeypatch):
    monkeypatch.setattr(utils.timeouts, "helm_install_timeout", 7)
    helm, calls = fake_helm()

    success, *_ = _install(
        utils, f"{helm} -n ns install r chart.tgz -o json", platforms=True
    )

    assert success
    assert "--timeout 21s" in calls.read_text()


def test_existing_timeout_is_kept_and_never_killed(utils, fake_helm, monkeypatch):
    monkeypatch.setattr(utils.timeouts, "helm_install_timeout", 1)
    monkeypatch.setattr(utils.timeouts, "helm_kill_factor", 1)
    monkeypatch.setattr(utils.timeouts, "shell_cmd_default_timeout", 1)
    helm, calls = fake_helm(seconds=2)

    success, *_ = _install(
        utils, f"{helm} -n ns install r chart.tgz -o json --wait --timeout 5m"
    )

    assert success
    args = calls.read_text().split()
    assert args.count("--timeout") == 1
    assert args[-2:] == ["--timeout", "5m"]


def test_timeout_goes_to_the_install_not_a_shell_suffix(utils, fake_helm):
    helm, calls = fake_helm()

    success, *_ = _install(
        utils, f"{helm} -n ns install r chart.tgz -o json ; {helm} -n ns delete r"
    )

    assert success
    install, delete = calls.read_text().splitlines()
    assert "--timeout" in install.split()
    assert "--timeout" not in delete.split()


def test_hung_install_is_killed_far_past_the_limit(utils, fake_helm, monkeypatch):
    monkeypatch.setattr(utils.timeouts, "helm_install_timeout", 1)
    monkeypatch.setattr(utils.timeouts, "helm_kill_factor", 2)
    helm, _ = fake_helm(seconds=4)

    with pytest.raises(subprocess.TimeoutExpired) as killed:
        _install(utils, f"{helm} -n ns install r chart.tgz -o json")

    assert killed.value.timeout == 2


def test_command_without_a_limit_gets_the_default(utils, monkeypatch):
    monkeypatch.setattr(utils.timeouts, "shell_cmd_default_timeout", 1)

    with pytest.raises(subprocess.TimeoutExpired) as killed:
        utils.helm_helper.execute_shell_command("sleep 3", shell=True)

    assert killed.value.timeout == 1


def test_platform_delete_running_past_the_limit_is_not_killed(
    utils, fake_helm, monkeypatch
):
    monkeypatch.setattr(utils.timeouts, "helm_deletion_timeout", 1)
    helm, calls = fake_helm(seconds=4)
    monkeypatch.setattr(utils.settings, "helm_path", helm)

    success, _ = utils.helm_delete("r", helm_namespace="ns", platforms=True)

    assert success
    assert calls.read_text().split() == [
        "-n", "ns", "uninstall", "--timeout", "3s", "r"
    ]  # fmt: skip


def test_extension_delete_keeps_helms_default_limit(utils, fake_helm, monkeypatch):
    helm, calls = fake_helm()
    monkeypatch.setattr(utils.settings, "helm_path", helm)

    utils.helm_delete("r", helm_namespace="ns")

    for _ in range(50):  # the delete runs in the background
        if calls.exists() and calls.read_text():
            break
        time.sleep(0.1)
    assert calls.read_text().split() == ["-n", "ns", "uninstall", "r"]
