"""Integration tests — library level.

Requires a running Docker daemon. Run with:
    pytest lib/kaapana_extensions/tests/integration/ -m integration
"""

import json
import pytest

pytestmark = pytest.mark.integration


class TestPushPullRoundtrip:
    def test_push_returns_tag(self, client, ext_archive):
        tag = client.push(ext_archive)
        assert tag.endswith("-v1.0.0")

    def test_list_tags_after_push(self, client, ext_archive):
        tag = client.push(ext_archive)
        assert tag in client.list_tags()

    def test_get_extension_returns_manifest(self, client, ext_archive):
        tag = client.push(ext_archive)
        manifest = client.get_extension(tag)
        assert manifest["name"] == "my-ext"
        assert manifest["version"] == "1.0.0"

    def test_pull_manifest_roundtrip(self, client, ext_archive, tmp_path):
        tag = client.push(ext_archive)
        out = tmp_path / "pulled"
        client.pull(tag, out)
        pulled = json.loads((out / "extension_manifest.json").read_text())
        assert pulled["name"] == "my-ext"
        assert pulled["version"] == "1.0.0"

    def test_pull_files_roundtrip(self, client, ext_archive, tmp_path):
        tag = client.push(ext_archive)
        out = tmp_path / "pulled"
        client.pull(tag, out)
        chart = out / "charts" / "Chart.yaml"
        assert chart.exists()
        assert "my-ext" in chart.read_text()

    def test_delete_removes_tag(self, client, ext_archive):
        tag = client.push(ext_archive)
        assert tag in client.list_tags()
        assert client.delete_tag(tag) is True
        assert tag not in client.list_tags()

    def test_push_duplicate_raises(self, client, ext_archive):
        client.push(ext_archive)
        with pytest.raises(ValueError, match="already exists"):
            client.push(ext_archive)

    def test_push_overwrite_succeeds(self, client, ext_archive):
        tag = client.push(ext_archive)
        tag2 = client.push(ext_archive, overwrite=True)
        assert tag == tag2

    def test_push_bump_patch_creates_new_tag(self, client, ext_archive):
        client.push(ext_archive)
        bumped = client.push(ext_archive, bump="patch")
        assert bumped.endswith("-v1.0.1")
        assert bumped in client.list_tags()
