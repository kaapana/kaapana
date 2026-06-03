import io
import json
import tarfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from requests import HTTPError

from kaapana_extensions.extensions import ExtensionUtilityLibrary


_STABLE_ID = "aaaaaaaa-0000-0000-0000-000000000001"
_STABLE_TAG = f"{_STABLE_ID}-v1.0.0"


@pytest.fixture
def lib():
    instance = ExtensionUtilityLibrary(
        registry="https://registry.example.com",
        repo="user/repo",
        username="user",
        password="pass",
    )
    instance._manager = MagicMock()
    instance.logger = MagicMock()
    return instance


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


class TestCheckLogin:
    def test_success(self, lib):
        resp = MagicMock()
        resp.status_code = 200
        lib._manager._request_with_auth_retry.return_value = resp
        lib._manager.registry_url = "https://registry.example.com"
        assert lib.check_login() is True

    def test_failure_exception_returns_false(self, lib):
        lib._manager._request_with_auth_retry.side_effect = Exception("connection refused")
        lib._manager.registry_url = "https://registry.example.com"
        assert lib.check_login() is False


class TestListTags:
    def test_delegates_to_manager(self, lib):
        lib._manager.list_tags.return_value = ["v1.0.0", "v2.0.0"]
        assert lib.list_tags() == ["v1.0.0", "v2.0.0"]


class TestGetExtension:
    def test_returns_extension_manifest(self, lib):
        manifest = {"name": "my-ext", "version": "1.0.0"}
        lib._manager.get.return_value = {
            "user_metadata": {"extension_manifest": manifest}
        }
        result = lib.get_extension("v1.0.0")
        assert result == manifest

    def test_get_extensions_single_tag(self, lib):
        manifest = {"name": "my-ext", "version": "1.0.0"}
        lib._manager.get.return_value = {
            "user_metadata": {"extension_manifest": manifest}
        }
        result = lib.get_extensions("v1.0.0")
        assert result == [manifest]

    def test_get_extensions_all_tags(self, lib):
        lib._manager.list_tags.return_value = ["v1.0.0", "v2.0.0"]
        manifests = [
            {"name": "my-ext", "version": "1.0.0"},
            {"name": "my-ext", "version": "2.0.0"},
        ]
        lib._manager.get.side_effect = [
            {"user_metadata": {"extension_manifest": m}} for m in manifests
        ]
        result = lib.get_extensions()
        assert len(result) == 2
        assert result[0]["version"] == "1.0.0"
        assert result[1]["version"] == "2.0.0"


class TestPull:
    def test_success_writes_extension_manifest_and_returns_output_dir(self, lib, tmp_path):
        lib._manager.download_files.return_value = True
        ext_manifest = {"name": "my-ext", "version": "1.0.0"}
        lib._manager.get.return_value = {
            "user_metadata": {"extension_manifest": ext_manifest}
        }
        result = lib.pull("v1.0.0", tmp_path)
        assert result == tmp_path
        manifest_file = tmp_path / "extension_manifest.json"
        assert manifest_file.exists()
        assert json.loads(manifest_file.read_text()) == ext_manifest

    def test_download_files_false_raises_runtime_error(self, lib, tmp_path):
        lib._manager.download_files.return_value = False
        with pytest.raises(RuntimeError, match="Failed to download files"):
            lib.pull("nonexistent", tmp_path)


class TestPush:
    def test_succeeds_returns_stable_tag(self, lib, ext_archive):
        lib._manager.list_tags.return_value = []
        lib._manager.create_or_update_tag.return_value = True
        tag = lib.push(ext_archive)
        assert tag == _STABLE_TAG

    def test_duplicate_tag_raises_without_overwrite(self, lib, ext_archive):
        lib._manager.list_tags.return_value = [_STABLE_TAG]
        with pytest.raises(ValueError, match="already exists"):
            lib.push(ext_archive)

    def test_duplicate_tag_succeeds_with_overwrite(self, lib, ext_archive):
        lib._manager.list_tags.return_value = [_STABLE_TAG]
        lib._manager.create_or_update_tag.return_value = True
        tag = lib.push(ext_archive, overwrite=True)
        assert tag == _STABLE_TAG

    def test_missing_id_raises(self, lib, tmp_path):
        archive = _make_archive(tmp_path, {"name": "my-ext", "version": "1.0.0", "contents": []})
        with pytest.raises(ValueError, match="'name', 'id', and 'version'"):
            lib.push(archive)

    def test_bump_patch_creates_incremented_tag(self, lib, ext_archive):
        lib._manager.list_tags.return_value = [_STABLE_TAG]
        lib._manager.create_or_update_tag.return_value = True
        tag = lib.push(ext_archive, bump="patch")
        assert tag == f"{_STABLE_ID}-v1.0.1"

    def test_directory_source_raises(self, lib, tmp_path):
        with pytest.raises(ValueError, match="expects a .tar.gz archive"):
            lib.push(tmp_path)
