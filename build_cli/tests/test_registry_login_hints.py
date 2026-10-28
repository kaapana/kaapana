from unittest.mock import patch

from build_cli.build import BuildConfig  # noqa: F401  (import order avoids a circular import)
from build_cli.container import ContainerHelper
from helpers import make_config


def login_hints(config, registry: str):
    """Return the hints that the login command gets."""
    with (
        patch.object(ContainerHelper, "_build_config", config),
        patch("build_cli.container.container_helper.CommandUtils.run") as run,
    ):
        ContainerHelper.container_registry_login(registry=registry, username="user", password="password")
    login_call = [call for call in run.call_args_list if call.kwargs["context"] == "registry-login"][0]
    return login_call.kwargs["hints"]


def test_login_has_no_hints_without_plain_http():
    assert not login_hints(make_config(), "10.0.0.5:5000")


def test_login_hints_name_the_registry_with_plain_http():
    hints = login_hints(make_config(plain_http=True), "10.0.0.5:5000/kaapana")
    assert '"10.0.0.5:5000"' in hints[0]
    assert any("/etc/docker/daemon.json" in hint for hint in hints)
