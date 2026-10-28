import tempfile
import tomllib
from pathlib import Path
from unittest.mock import patch

from build_cli.build import BuildConfig
from build_cli.container import ContainerHelper
from helpers import make_config


def read_config(config: BuildConfig, nameservers: list) -> dict | None:
    """Return the parsed buildkitd config that the helper writes, or None if it writes none."""
    with (
        tempfile.TemporaryDirectory() as tmp_dir,
        patch.object(ContainerHelper, "_build_config", config),
        patch.object(ContainerHelper, "_host_nameservers", return_value=nameservers),
    ):
        opts = ContainerHelper._buildx_buildkitd_config_opts(Path(tmp_dir))
        if not opts:
            return None
        assert opts[0] == "--buildkitd-config"
        return tomllib.loads(Path(opts[1]).read_text())


def test_no_config_without_plain_http_and_nameservers():
    assert read_config(make_config(), []) is None


def test_dns_only_without_plain_http():
    config = read_config(make_config(), ["10.0.0.1", "10.0.0.2"])
    assert config == {"dns": {"nameservers": ["10.0.0.1", "10.0.0.2"]}}


def test_plain_http_without_nameservers():
    config = read_config(make_config(plain_http=True), [])
    assert config == {"registry": {"10.0.0.5:5000": {"http": True, "insecure": True}}}


def test_plain_http_with_nameservers_keeps_dns():
    config = read_config(make_config(plain_http=True), ["10.0.0.1"])
    assert config["dns"] == {"nameservers": ["10.0.0.1"]}
    assert config["registry"] == {"10.0.0.5:5000": {"http": True, "insecure": True}}


def test_plain_http_strips_repository_path():
    config = read_config(make_config(plain_http=True, default_registry="10.0.0.5:5000/kaapana"), [])
    assert list(config["registry"]) == ["10.0.0.5:5000"]
