import logging
from pathlib import Path
from unittest.mock import patch

from build_cli.build import BuildConfig  # noqa: F401  (import order avoids a circular import)
from build_cli.container import ContainerHelper

STUB_RESOLV_CONF = "nameserver 127.0.0.53\noptions edns0 trust-ad\nsearch example.org\n"


def host_nameservers(tmp_path: Path, etc_resolv_conf: str | None, systemd_resolv_conf: str | None) -> list:
    """Return the nameservers that the helper reads from the given file contents. None means a missing file."""
    etc_path = tmp_path / "etc-resolv.conf"
    systemd_path = tmp_path / "systemd-resolv.conf"
    for path, content in ((etc_path, etc_resolv_conf), (systemd_path, systemd_resolv_conf)):
        if content is not None:
            path.write_text(content)

    with patch.object(ContainerHelper, "_RESOLV_CONF_PATHS", (etc_path, systemd_path)):
        return ContainerHelper._host_nameservers()


def test_static_resolv_conf_is_used(tmp_path):
    nameservers = host_nameservers(tmp_path, "nameserver 10.0.0.1\nnameserver 10.0.0.2\n", "nameserver 10.0.0.9\n")
    assert nameservers == ["10.0.0.1", "10.0.0.2"]


def test_systemd_resolved_upstream_servers_replace_the_stub(tmp_path):
    nameservers = host_nameservers(tmp_path, STUB_RESOLV_CONF, "nameserver 10.0.0.1\nnameserver 10.0.0.2\n")
    assert nameservers == ["10.0.0.1", "10.0.0.2"]


def test_missing_etc_resolv_conf_falls_back(tmp_path):
    assert host_nameservers(tmp_path, None, "nameserver 10.0.0.1\n") == ["10.0.0.1"]


def test_ipv6_loopback_is_dropped(tmp_path):
    assert host_nameservers(tmp_path, "nameserver ::1\nnameserver fd00::1\n", None) == ["fd00::1"]


def test_stub_only_warns_and_returns_nothing(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        assert host_nameservers(tmp_path, STUB_RESOLV_CONF, None) == []
    assert any("No nameserver outside of loopback" in record.message for record in caplog.records)
