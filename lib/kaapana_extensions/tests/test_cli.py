import io
import json
import tarfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typer.testing import CliRunner

from kaapana_containers.registries.registry import OCIError
from kaapana_extensions.cli import app

runner = CliRunner()

_STABLE_ID = "aaaaaaaa-0000-0000-0000-000000000001"
_STABLE_TAG = f"{_STABLE_ID}-v1.0.0"
_REGISTRY_OPTS = [
    "--registry", "https://registry.example.com",
    "--repo", "user/repo",
    "--user", "user",
    "--password", "pass",
]


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
    return _make_archive(
        tmp_path,
        {"name": "my-ext", "id": _STABLE_ID, "version": "1.0.0", "contents": []},
    )


def _mock_lib(return_values: dict | None = None, side_effects: dict | None = None):
    """Async context manager mock for ExtensionUtilityLibrary."""
    lib = AsyncMock()
    lib.__aenter__ = AsyncMock(return_value=lib)
    lib.__aexit__ = AsyncMock(return_value=None)
    for method, value in (return_values or {}).items():
        getattr(lib, method).return_value = value
    for method, effect in (side_effects or {}).items():
        getattr(lib, method).side_effect = effect
    return lib


# ---------------------------------------------------------------------------
# login / logout / whoami
# ---------------------------------------------------------------------------

class TestLogin:
    def test_success(self):
        with patch("kaapana_extensions.cli.oci_login"):
            result = runner.invoke(
                app,
                ["login", "--registry", "https://registry.example.com",
                 "--repo", "user/repo", "--user", "testuser", "--password", "testpass"],
            )
        assert result.exit_code == 0
        assert "LOGIN SUCCESSFUL" in result.output

    def test_failure_exits_1(self):
        with patch("kaapana_extensions.cli.oci_login", side_effect=Exception("bad credentials")):
            result = runner.invoke(
                app,
                ["login", "--registry", "r", "--repo", "r/r", "--user", "u", "--password", "bad"],
            )
        assert result.exit_code == 1
        assert "Login failed" in result.output


class TestWhoami:
    def test_logged_in_shows_session(self):
        creds = {"username": "u", "registry": "https://registry.example.com", "repo": "r/r", "password": "x"}
        with patch("kaapana_extensions.cli.get_credentials", return_value=creds):
            result = runner.invoke(app, ["whoami"])
        assert result.exit_code == 0
        assert "CURRENT SESSION" in result.output

    def test_not_logged_in_shows_hint(self):
        with patch("kaapana_extensions.cli.get_credentials", return_value=None):
            result = runner.invoke(app, ["whoami"])
        assert result.exit_code == 0
        assert "Not logged in" in result.output


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

class TestListCli:
    def test_exits_0_and_prints_tags(self):
        mock = _mock_lib(return_values={"list_tags": ["ext-v1.0.0", "ext-v2.0.0"]})
        with patch("kaapana_extensions.cli.ExtensionUtilityLibrary", return_value=mock):
            result = runner.invoke(app, ["list"] + _REGISTRY_OPTS)
        assert result.exit_code == 0
        assert "ext-v1.0.0" in result.output
        assert "ext-v2.0.0" in result.output

    def test_empty_repository_prints_no_extensions(self):
        mock = _mock_lib(return_values={"list_tags": []})
        with patch("kaapana_extensions.cli.ExtensionUtilityLibrary", return_value=mock):
            result = runner.invoke(app, ["list"] + _REGISTRY_OPTS)
        assert result.exit_code == 0
        assert "No extensions found" in result.output

    def test_name_unknown_exits_1(self):
        mock = _mock_lib(side_effects={"list_tags": OCIError("no repo", code="NAME_UNKNOWN")})
        with patch("kaapana_extensions.cli.ExtensionUtilityLibrary", return_value=mock):
            result = runner.invoke(app, ["list"] + _REGISTRY_OPTS)
        assert result.exit_code == 1
        assert "NAME_UNKNOWN" in result.output


# ---------------------------------------------------------------------------
# pull
# ---------------------------------------------------------------------------

class TestPullCli:
    def test_exits_0_and_prints_path(self, tmp_path):
        mock = _mock_lib(return_values={"pull": tmp_path})
        with patch("kaapana_extensions.cli.ExtensionUtilityLibrary", return_value=mock):
            result = runner.invoke(app, ["pull", "ext-v1.0.0", str(tmp_path)] + _REGISTRY_OPTS)
        assert result.exit_code == 0
        assert str(tmp_path) in result.output

    def test_manifest_unknown_exits_1(self, tmp_path):
        mock = _mock_lib(side_effects={"pull": OCIError("tag not found", code="MANIFEST_UNKNOWN")})
        with patch("kaapana_extensions.cli.ExtensionUtilityLibrary", return_value=mock):
            result = runner.invoke(app, ["pull", "nonexistent", str(tmp_path)] + _REGISTRY_OPTS)
        assert result.exit_code == 1
        assert "MANIFEST_UNKNOWN" in result.output


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------

class TestPushCli:
    def test_exits_0_and_prints_tag(self, ext_archive):
        mock = _mock_lib(return_values={"push": _STABLE_TAG})
        with patch("kaapana_extensions.cli.ExtensionUtilityLibrary", return_value=mock):
            result = runner.invoke(app, ["push", str(ext_archive)] + _REGISTRY_OPTS)
        assert result.exit_code == 0
        assert "Pushed" in result.output

    def test_source_not_found_exits_1(self, tmp_path):
        result = runner.invoke(app, ["push", str(tmp_path / "missing.tar.gz")] + _REGISTRY_OPTS)
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_duplicate_tag_exits_1(self, ext_archive):
        mock = _mock_lib(side_effects={"push": ValueError(f"Tag '{_STABLE_TAG}' already exists")})
        with patch("kaapana_extensions.cli.ExtensionUtilityLibrary", return_value=mock):
            result = runner.invoke(app, ["push", str(ext_archive)] + _REGISTRY_OPTS)
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_oci_error_exits_1(self, ext_archive):
        mock = _mock_lib(side_effects={"push": OCIError("upload failed", code="BLOB_UPLOAD_INVALID")})
        with patch("kaapana_extensions.cli.ExtensionUtilityLibrary", return_value=mock):
            result = runner.invoke(app, ["push", str(ext_archive)] + _REGISTRY_OPTS)
        assert result.exit_code == 1
        assert "BLOB_UPLOAD_INVALID" in result.output


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

class TestBuildCli:
    def test_local_build_prints_archive(self, ext_archive):
        with patch("kaapana_extensions.cli.ExtensionUtilityLibrary.build", return_value=[("./my-ext", ext_archive)]):
            result = runner.invoke(app, ["build", "./my-ext"])
        assert result.exit_code == 0
        assert "Archive:" in result.output

    def test_missing_id_exits_1(self):
        err = ValueError("extension_manifest.json is missing 'name', 'id', and 'version'")
        with patch("kaapana_extensions.cli.ExtensionUtilityLibrary.build", side_effect=err):
            result = runner.invoke(app, ["build", "./my-ext"])
        assert result.exit_code == 1
        assert "missing" in result.output.lower()

    def test_build_and_push_oci_error_exits_1(self, ext_archive):
        instance = _mock_lib(side_effects={"push": OCIError("denied", code="DENIED")})
        mock_class = MagicMock()
        mock_class.build = MagicMock(return_value=[("./my-ext", ext_archive)])
        mock_class.return_value = instance
        with patch("kaapana_extensions.cli.ExtensionUtilityLibrary", mock_class):
            result = runner.invoke(
                app,
                ["build", "./my-ext", "--push"] + _REGISTRY_OPTS,
            )
        assert result.exit_code == 1
        assert "DENIED" in result.output
