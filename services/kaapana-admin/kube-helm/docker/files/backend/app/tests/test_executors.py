import asyncio

import pytest

from app import helm_helper
from app.config import settings


def shell_payloads(marker):
    return [f"x; touch {marker}", f"$(touch {marker})", f"`touch {marker}`", f"x | touch {marker}"]


def test_blocking_argument_list_runs_without_shell(fake_cli, marker):
    for payload in shell_payloads(marker):
        success, _ = helm_helper.execute_shell_command([settings.helm_path, "show", "chart", payload])

        assert success
        assert fake_cli.calls()[-1] == ["show", "chart", payload]
    assert not marker.exists()


def test_non_blocking_argument_list_runs_without_shell(fake_cli, marker):
    for payload in shell_payloads(marker):
        success, _ = helm_helper.execute_shell_command(
            [settings.helm_path, "show", "chart", payload],
            blocking=False,
        )

        assert success
        assert fake_cli.wait_for_calls(payload) == [["show", "chart", payload]]
    assert not marker.exists()


def test_async_argument_list_runs_without_shell(fake_cli, marker):
    for payload in shell_payloads(marker):
        success, _ = asyncio.run(helm_helper.exec_shell_cmd_async([settings.helm_path, "show", "chart", payload]))

        assert success
        assert fake_cli.calls()[-1] == ["show", "chart", payload]
    assert not marker.exists()


@pytest.mark.parametrize("blocking", [True, False])
def test_missing_executable_is_reported_as_failure(tmp_path, blocking):
    success, message = helm_helper.execute_shell_command([str(tmp_path / "missing"), "ls"], blocking=blocking)

    assert not success
    assert message


def test_failed_status_check_returns_stderr(fake_cli):
    success, _ = helm_helper.execute_shell_command([settings.helm_path, "-n", "default", "status", "demo"])

    assert not success


@pytest.mark.parametrize(
    "command, expected",
    [
        (["helm", "uninstall", "--timeout=40s", "demo"], True),
        (["helm", "uninstall", "--timeout", "40s", "demo"], True),
        (["helm", "uninstall", "demo"], False),
        (["helm", "uninstall", "--timeout-like-name"], False),
    ],
)
def test_timeout_flag_is_detected_in_argument_lists(command, expected):
    assert helm_helper.has_timeout_flag(command) is expected


@pytest.mark.parametrize("command", ["helm ls", b"helm ls"])
def test_string_commands_are_rejected(command):
    with pytest.raises(TypeError):
        helm_helper.execute_shell_command(command)
    with pytest.raises(TypeError):
        helm_helper.execute_shell_command(command, blocking=False)
    with pytest.raises(TypeError):
        asyncio.run(helm_helper.exec_shell_cmd_async(command))
