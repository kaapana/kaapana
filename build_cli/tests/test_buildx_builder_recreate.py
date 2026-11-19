from subprocess import CompletedProcess
from unittest.mock import patch

import pytest
from build_cli.build import BuildConfig  # noqa: F401  (import order avoids a circular import)
from build_cli.container import ContainerHelper
from helpers import make_config


def run_ensure_builder(config, builder_exists: bool) -> list:
    """Return the buildx subcommands that ensure_buildx_builder runs."""

    def fake_run(command, **kwargs):
        return CompletedProcess(command, 0 if (builder_exists or command[2] != "inspect") else 1, "", "")

    with (
        patch.object(ContainerHelper, "_build_config", config),
        patch.object(ContainerHelper, "_buildx_buildkitd_config_opts", return_value=[]),
        patch("build_cli.container.container_helper.CommandUtils.run", side_effect=fake_run) as run,
    ):
        ContainerHelper.ensure_buildx_builder()
    return [call.args[0][2] for call in run.call_args_list]


def test_existing_builder_is_reused_without_registry_settings():
    assert run_ensure_builder(make_config(), builder_exists=True) == ["inspect"]


@pytest.mark.parametrize("settings", [{"plain_http": True}, {"docker_io_mirrors": ["mirror.gcr.io"]}])
def test_existing_builder_is_recreated_with_registry_settings(settings):
    commands = run_ensure_builder(make_config(**settings), builder_exists=True)
    assert commands == ["inspect", "rm", "create"]


def test_missing_builder_is_created_with_plain_http():
    commands = run_ensure_builder(make_config(plain_http=True), builder_exists=False)
    assert commands == ["inspect", "create"]


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        ({}, []),
        ({"plain_http": True}, ["--plain-http"]),
        ({"docker_io_mirrors": ["mirror.gcr.io"]}, ["--docker-io-mirror"]),
        ({"plain_http": True, "docker_io_mirrors": ["mirror.gcr.io"]}, ["--plain-http", "--docker-io-mirror"]),
    ],
)
def test_registry_flags_are_the_ones_set(settings, expected):
    with patch.object(ContainerHelper, "_build_config", make_config(**settings)):
        assert ContainerHelper._buildx_registry_flags() == expected
