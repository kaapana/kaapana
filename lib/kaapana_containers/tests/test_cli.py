import json
import pytest
from unittest.mock import AsyncMock, patch
from typer.testing import CliRunner

from kaapana_containers.registries.cli import app
from kaapana_containers.registries.registry import OCIError

runner = CliRunner()


def _mock_client(return_values: dict | None = None, side_effects: dict | None = None):
    """Build a mock OCIRegistryDiscovery that works as an async context manager."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    for method, value in (return_values or {}).items():
        getattr(client, method).return_value = value
    for method, effect in (side_effects or {}).items():
        getattr(client, method).side_effect = effect
    return client


REGISTRY = "https://registry.example.com"
REPO = "user/repo"


class TestListTagsCli:
    def test_exits_0_and_prints_tags(self):
        mock = _mock_client(return_values={"list_tags": ["v1.0.0", "v2.0.0"]})
        with patch("kaapana_containers.registries.cli.OCIRegistryDiscovery", return_value=mock):
            result = runner.invoke(app, ["list-tags", REGISTRY, REPO])
        assert result.exit_code == 0
        assert "v1.0.0" in result.output
        assert "v2.0.0" in result.output

    def test_oci_error_exits_1(self):
        mock = _mock_client(
            side_effects={"list_tags": OCIError("not found", code="NAME_UNKNOWN")}
        )
        with patch("kaapana_containers.registries.cli.OCIRegistryDiscovery", return_value=mock):
            result = runner.invoke(app, ["list-tags", REGISTRY, REPO])
        assert result.exit_code == 1
        assert "NAME_UNKNOWN" in result.output

    def test_empty_repository_prints_no_tags(self):
        mock = _mock_client(return_values={"list_tags": []})
        with patch("kaapana_containers.registries.cli.OCIRegistryDiscovery", return_value=mock):
            result = runner.invoke(app, ["list-tags", REGISTRY, REPO])
        assert result.exit_code == 0
        assert "No tags found" in result.output


class TestPublishCli:
    def test_exits_0_on_success(self, tmp_path):
        metadata_file = tmp_path / "meta.json"
        metadata_file.write_text(json.dumps({"name": "ext", "version": "1.0.0"}))
        mock = _mock_client(return_values={"create_or_update_tag": True})
        with patch("kaapana_containers.registries.cli.OCIRegistryDiscovery", return_value=mock):
            result = runner.invoke(
                app, ["publish", REGISTRY, REPO, "v1.0.0", str(metadata_file)]
            )
        assert result.exit_code == 0
        assert "Successfully published" in result.output

    def test_oci_error_exits_1(self, tmp_path):
        metadata_file = tmp_path / "meta.json"
        metadata_file.write_text(json.dumps({"name": "ext"}))
        mock = _mock_client(
            side_effects={"create_or_update_tag": OCIError("upload failed", code="BLOB_UPLOAD_INVALID")}
        )
        with patch("kaapana_containers.registries.cli.OCIRegistryDiscovery", return_value=mock):
            result = runner.invoke(
                app, ["publish", REGISTRY, REPO, "v1.0.0", str(metadata_file)]
            )
        assert result.exit_code == 1
        assert "BLOB_UPLOAD_INVALID" in result.output


class TestDeleteCli:
    def test_exits_0_on_success(self):
        mock = _mock_client(return_values={"delete_tag": True})
        with patch("kaapana_containers.registries.cli.OCIRegistryDiscovery", return_value=mock):
            result = runner.invoke(app, ["delete", REGISTRY, REPO, "v1.0.0"])
        assert result.exit_code == 0
        assert "Successfully deleted" in result.output

    def test_oci_error_exits_1(self):
        mock = _mock_client(
            side_effects={"delete_tag": OCIError("unknown tag", code="MANIFEST_UNKNOWN")}
        )
        with patch("kaapana_containers.registries.cli.OCIRegistryDiscovery", return_value=mock):
            result = runner.invoke(app, ["delete", REGISTRY, REPO, "v1.0.0"])
        assert result.exit_code == 1
        assert "MANIFEST_UNKNOWN" in result.output
