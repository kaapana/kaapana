"""Integration tests — CLI level.

Same flows as test_push_pull but exercised through the Typer CLI, verifying
that commands produce the right output and exit codes against a real registry.
"""

import pytest
from typer.testing import CliRunner

from kaapana_extensions.cli import app

pytestmark = pytest.mark.integration

runner = CliRunner()


def _push(registry_opts, ext_archive):
    result = runner.invoke(app, ["push", str(ext_archive)] + registry_opts)
    assert result.exit_code == 0, result.output
    return result.output.split("Pushed: ")[1].strip()


class TestCliPush:
    def test_push_exits_0_and_prints_tag(self, registry_opts, ext_archive):
        result = runner.invoke(app, ["push", str(ext_archive)] + registry_opts)
        assert result.exit_code == 0
        assert "Pushed:" in result.output

    def test_push_nonexistent_source_exits_1(self, registry_opts):
        result = runner.invoke(app, ["push", "/does/not/exist.tar.gz"] + registry_opts)
        assert result.exit_code == 1

    def test_push_duplicate_exits_1_with_error_message(self, registry_opts, ext_archive):
        _push(registry_opts, ext_archive)
        result = runner.invoke(app, ["push", str(ext_archive)] + registry_opts)
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_push_overwrite_exits_0_and_returns_same_tag(self, registry_opts, ext_archive):
        tag = _push(registry_opts, ext_archive)
        result = runner.invoke(app, ["push", str(ext_archive), "--overwrite"] + registry_opts)
        assert result.exit_code == 0
        assert f"Pushed: {tag}" in result.output


class TestCliList:
    def test_pushed_tag_appears_in_list(self, registry_opts, ext_archive):
        tag = _push(registry_opts, ext_archive)
        result = runner.invoke(app, ["list"] + registry_opts)
        assert result.exit_code == 0
        assert tag in result.output


class TestCliPull:
    def test_pull_creates_manifest_file(self, registry_opts, ext_archive, tmp_path):
        tag = _push(registry_opts, ext_archive)
        out = tmp_path / "pulled"
        result = runner.invoke(app, ["pull", tag, str(out)] + registry_opts)
        assert result.exit_code == 0
        assert (out / "extension_manifest.json").exists()

    def test_pull_missing_tag_exits_1(self, registry_opts, tmp_path):
        result = runner.invoke(
            app, ["pull", "nonexistent-v9.9.9", str(tmp_path)] + registry_opts
        )
        assert result.exit_code == 1


class TestCliDelete:
    def test_delete_tag_exits_0_and_removes_from_list(self, registry_opts, ext_archive):
        tag = _push(registry_opts, ext_archive)
        result = runner.invoke(app, ["delete", tag, "--yes"] + registry_opts)
        assert result.exit_code == 0
        assert "Deleted:" in result.output

        result = runner.invoke(app, ["list"] + registry_opts)
        assert tag not in result.output
