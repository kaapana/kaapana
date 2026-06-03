import io
import json
import tarfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from kaapana_extensions.cli import app

runner = CliRunner()


_STABLE_ID = "aaaaaaaa-0000-0000-0000-000000000001"
_STABLE_TAG = f"{_STABLE_ID}-v1.0.0"


def _make_archive(tmp_path: Path, manifest: dict) -> Path:
    archive = tmp_path / f"{manifest.get('name', 'ext')}-v{manifest.get('version', '0.0.0')}.tar.gz"
    manifest_bytes = json.dumps(manifest).encode()
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo(name="extension_manifest.json")
        info.size = len(manifest_bytes)
        tar.addfile(info, io.BytesIO(manifest_bytes))
    return archive


@pytest.fixture
def ext_archive(tmp_path):
    manifest = {
        "name": "my-ext",
        "id": _STABLE_ID,
        "version": "1.0.0",
        "contents": [],
    }
    return _make_archive(tmp_path, manifest)


class TestLogin:
    def test_success(self):
        with patch("kaapana_extensions.cli.oci_login") as mock_login:
            mock_login.return_value = None
            result = runner.invoke(
                app,
                [
                    "login",
                    "--registry", "https://registry.example.com",
                    "--repo", "user/repo",
                    "--user", "testuser",
                    "--password", "testpass",
                ],
            )
        assert result.exit_code == 0
        assert "LOGIN SUCCESSFUL" in result.output

    def test_failure_propagates(self):
        with patch("kaapana_extensions.cli.oci_login") as mock_login:
            mock_login.side_effect = Exception("bad credentials")
            result = runner.invoke(
                app,
                [
                    "login",
                    "--registry", "https://registry.example.com",
                    "--repo", "user/repo",
                    "--user", "testuser",
                    "--password", "wrongpass",
                ],
            )
        assert result.exit_code == 1
        assert "Error: Login failed" in result.output


class TestPull:
    def test_bare_tag_success(self, tmp_path):
        mock_client = MagicMock()
        mock_client.pull.return_value = tmp_path
        with patch("kaapana_extensions.cli._get_client", return_value=mock_client):
            result = runner.invoke(
                app,
                ["pull", "v1.0.0", str(tmp_path)],
            )
        assert result.exit_code == 0
        assert str(tmp_path) in result.output

    def test_tag_not_found_prints_error_and_exits_1(self, tmp_path):
        mock_client = MagicMock()
        mock_client.pull.side_effect = RuntimeError("Failed to download files for tag 'v999'")
        with patch("kaapana_extensions.cli._get_client", return_value=mock_client):
            result = runner.invoke(
                app,
                ["pull", "v999", str(tmp_path)],
            )
        assert result.exit_code == 1


class TestPush:
    def test_success_prints_tag(self, tmp_path, ext_archive):
        mock_client = MagicMock()
        mock_client.push.return_value = _STABLE_TAG
        with patch("kaapana_extensions.cli._get_client", return_value=mock_client):
            result = runner.invoke(app, ["push", str(ext_archive)])
        assert result.exit_code == 0
        assert _STABLE_TAG in result.output

    def test_source_not_found_exits_1(self, tmp_path):
        mock_client = MagicMock()
        with patch("kaapana_extensions.cli._get_client", return_value=mock_client):
            result = runner.invoke(app, ["push", str(tmp_path / "missing.tar.gz")])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_duplicate_exits_1(self, tmp_path, ext_archive):
        mock_client = MagicMock()
        mock_client.push.side_effect = ValueError(f"Tag '{_STABLE_TAG}' already exists")
        with patch("kaapana_extensions.cli._get_client", return_value=mock_client):
            result = runner.invoke(app, ["push", str(ext_archive)])
        assert result.exit_code == 1
        assert "already exists" in result.output


class TestBuild:
    def test_local_build_success(self, tmp_path, ext_archive):
        archives = [("./my-ext", ext_archive)]
        with patch("kaapana_extensions.cli.ExtensionUtilityLibrary.build", return_value=archives):
            result = runner.invoke(app, ["build", "./my-ext"])
        assert result.exit_code == 0
        assert "Archive:" in result.output

    def test_push_flag_duplicate_exits_1(self, tmp_path, ext_archive):
        archives = [("./my-ext", ext_archive)]
        mock_client = MagicMock()
        mock_client.push.side_effect = ValueError(f"Tag '{_STABLE_TAG}' already exists")
        with patch("kaapana_extensions.cli.ExtensionUtilityLibrary.build", return_value=archives), \
             patch("kaapana_extensions.cli._get_client", return_value=mock_client):
            result = runner.invoke(
                app,
                ["build", "./my-ext", "--push",
                 "--registry", "r", "--repo", "r/r", "--user", "u", "--password", "p"],
            )
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_git_source_missing_id_exits_1(self):
        err = ValueError(
            "extension_manifest.json is missing an 'id' field."
        )
        with patch("kaapana_extensions.cli.ExtensionUtilityLibrary.build", side_effect=err):
            result = runner.invoke(app, ["build", "https://git.example.com/repo.git"])
        assert result.exit_code == 1
        assert "missing" in result.output.lower()


class TestWhoami:
    def test_logged_in_shows_session(self):
        creds = {
            "username": "testuser",
            "registry": "https://registry.example.com",
            "repo": "user/repo",
            "password": "secret",
        }
        with patch("kaapana_extensions.cli.get_credentials", return_value=creds):
            result = runner.invoke(app, ["whoami"])
        assert result.exit_code == 0
        assert "CURRENT SESSION" in result.output
        assert "testuser" in result.output

    def test_not_logged_in_shows_helpful_message(self):
        with patch("kaapana_extensions.cli.get_credentials", return_value=None):
            result = runner.invoke(app, ["whoami"])
        assert result.exit_code == 0
        assert "Not logged in" in result.output
