"""Unit tests for the write-back task.

The module imports ``data_api`` at top (installed in the base image) but only
imports kaapanapy lazily inside ``_amain``. We load it by path, swap in fake
DataClient/StorageClient, inject a fake kaapanapy token helper, and assert the
upload → create-entity → attach-metadata orchestration (and that provenance is
built from run-context env, not the manifest).
"""

import asyncio
import importlib.util
import json
import pathlib
import sys
import types

import pytest

MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "files" / "upload_to_data_api.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("upload_standalone", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeStorage:
    def __init__(self, *a, **k):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def upload(self, files, store, target):
        self.calls.append({"files": list(files), "store": store, "target": target})
        return [{"type": "s3", "bucket": target["bucket"], "key": "k/model.dummy"}]


class _FakeData:
    def __init__(self, *a, **k):
        self.created = None
        self.attached = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def create_entity(self, entity):
        self.created = entity

    async def attach_metadata(self, entity_id, key, data):
        self.attached.append((entity_id, key, data))


class _FakeResp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._p


def _install_aii(mod, monkeypatch, mapping=None):
    """Fake the AII project lookup ``_project_bucket`` does via ``httpx.get``.

    ``mapping`` maps a project identifier (the last URL path segment, i.e.
    ``KAAPANA_PROJECT_IDENTIFIER``) to its ``s3_bucket``; unknown identifiers fall
    back to ``project-{identifier}``. Pass ``{ident: None}`` to simulate AII
    returning no bucket.
    """
    mapping = mapping or {}

    def fake_get(url, *a, **k):
        ident = url.rstrip("/").rsplit("/", 1)[-1]
        bucket = mapping.get(ident, f"project-{ident}")
        return _FakeResp({"s3_bucket": bucket})

    monkeypatch.setattr(mod.httpx, "get", fake_get)


def _prep(mod, tmp_path, monkeypatch, *, manifest):
    channel = tmp_path / "results"
    channel.mkdir()
    (channel / "model.dummy").write_text("weights")
    (channel / "upload_manifest.json").write_text(json.dumps(manifest))

    storage, data = _FakeStorage(), _FakeData()
    monkeypatch.setattr(mod, "StorageClient", lambda *a, **k: storage)
    monkeypatch.setattr(mod, "DataClient", lambda *a, **k: data)
    # Default: AII resolves any identifier to "project-{identifier}". Tests that
    # need a specific bucket (or a missing one) re-install with an explicit mapping.
    _install_aii(mod, monkeypatch)

    fake_helper = types.ModuleType("kaapanapy.helper")
    fake_helper.get_project_user_access_token = lambda: "tok"
    kaapanapy = types.ModuleType("kaapanapy")
    kaapanapy.helper = fake_helper
    monkeypatch.setitem(sys.modules, "kaapanapy", kaapanapy)
    monkeypatch.setitem(sys.modules, "kaapanapy.helper", fake_helper)

    # Run-context env the operator injects (individual tests may override/clear).
    monkeypatch.setenv("KAAPANA_DAG_ID", "data-api-finetune-demo_v1")
    monkeypatch.setenv("KAAPANA_WORKFLOW_RUN_ID", "run-1")

    monkeypatch.setattr("sys.argv", ["upload_to_data_api.py", "-i", str(channel)])
    return storage, data


_MANIFEST = {
    "store": "s3",
    "metadata": {"model": {"name": "dummy", "trained_from_scratch": True}},
    "upstream_entity_ids": ["seg-1", "seg-2"],
}


def test_upload_creates_entity_with_card_and_provenance(tmp_path, monkeypatch):
    mod = _load()
    storage, data = _prep(mod, tmp_path, monkeypatch, manifest=_MANIFEST)

    monkeypatch.setenv("KAAPANA_PROJECT_IDENTIFIER", "proj")
    monkeypatch.setenv("KAAPANA_DAG_ID", "data-api-finetune-demo_v1")
    monkeypatch.setenv("KAAPANA_WORKFLOW_RUN_ID", "run-7")
    monkeypatch.setenv("KAAPANA_TASK_ID", "upload_model")
    monkeypatch.setenv("KAAPANA_IMAGE", "reg/data-api-upload:1")

    mod.main()

    # Uploaded the model file (not the manifest) to the project bucket under a
    # per-run prefix.
    assert len(storage.calls) == 1
    call = storage.calls[0]
    assert call["store"] == "s3"
    # AII resolves project "proj" to bucket "project-proj" (default fake mapping).
    assert call["target"]["bucket"] == "project-proj"
    assert call["target"]["key_prefix"].startswith("data-api/")
    assert [name for name, _ in call["files"]] == ["model.dummy"]

    # Minted an entity with the returned coordinate.
    assert data.created["storage_coordinates"][0]["type"] == "s3"
    new_id = data.created["id"]

    attached = {key: value for (eid, key, value) in data.attached if eid == new_id}
    # model came from the manifest.
    assert attached["model"]["name"] == "dummy"
    # provenance came from the trusted run-context env, NOT the manifest.
    prov = attached["provenance"]
    assert prov["workflow_name"] == "data-api-finetune-demo_v1"
    assert prov["workflow_run_id"] == "run-7"
    assert prov["task_id"] == "upload_model"
    assert prov["project"] == "proj"
    assert prov["upstream_entity_ids"] == ["seg-1", "seg-2"]
    assert "produced_at" in prov


def test_upload_bucket_resolved_from_aii(tmp_path, monkeypatch):
    # The bucket is the authoritative Project.s3_bucket returned by AII, keyed by
    # the project UUID — including the admin project, whose bucket "project-admin"
    # is NOT derivable from its UUID. This is the regression for the wrong-bucket
    # AccessDenied seen in the admin project.
    mod = _load()
    storage, _ = _prep(mod, tmp_path, monkeypatch, manifest=_MANIFEST)
    monkeypatch.delenv("UPLOAD_S3_BUCKET", raising=False)
    admin_uuid = "cddaf4ce-24a0-46ee-ac65-e22aaa8b6038"
    monkeypatch.setenv("KAAPANA_PROJECT_IDENTIFIER", admin_uuid)
    _install_aii(mod, monkeypatch, {admin_uuid: "project-admin"})
    mod.main()
    assert storage.calls[0]["target"]["bucket"] == "project-admin"


def test_upload_bucket_override_wins(tmp_path, monkeypatch):
    # An explicit UPLOAD_S3_BUCKET override beats the AII-resolved project bucket
    # (and AII is not consulted at all).
    mod = _load()
    storage, _ = _prep(mod, tmp_path, monkeypatch, manifest=_MANIFEST)
    monkeypatch.setenv("UPLOAD_S3_BUCKET", "explicit-bucket")
    monkeypatch.setenv(
        "KAAPANA_PROJECT_IDENTIFIER", "04b73a5d-dead-beef-0000-000000000000"
    )

    def _boom(*a, **k):  # AII must not be called when the override is set
        raise AssertionError("AII should not be queried when UPLOAD_S3_BUCKET is set")

    monkeypatch.setattr(mod.httpx, "get", _boom)
    mod.main()
    assert storage.calls[0]["target"]["bucket"] == "explicit-bucket"


def test_upload_fails_when_aii_returns_no_bucket(tmp_path, monkeypatch):
    # If AII has no s3_bucket for the project, fail loud rather than guess.
    mod = _load()
    _prep(mod, tmp_path, monkeypatch, manifest=_MANIFEST)
    monkeypatch.delenv("UPLOAD_S3_BUCKET", raising=False)
    monkeypatch.setenv("KAAPANA_PROJECT_IDENTIFIER", "proj")
    _install_aii(mod, monkeypatch, {"proj": None})
    with pytest.raises(RuntimeError, match="no s3_bucket"):
        mod.main()


def test_upload_fails_loud_without_run_context_env(tmp_path, monkeypatch):
    mod = _load()
    _prep(mod, tmp_path, monkeypatch, manifest=_MANIFEST)
    # Simulate the operator env-injection NOT reaching the pod.
    monkeypatch.delenv("KAAPANA_DAG_ID", raising=False)
    monkeypatch.delenv("KAAPANA_WORKFLOW_RUN_ID", raising=False)
    with pytest.raises(RuntimeError, match="run-context env"):
        mod.main()


def test_upload_fails_without_manifest(tmp_path, monkeypatch):
    mod = _load()
    channel = tmp_path / "results"
    channel.mkdir()
    (channel / "model.dummy").write_text("w")
    fake_helper = types.ModuleType("kaapanapy.helper")
    fake_helper.get_project_user_access_token = lambda: "tok"
    kaapanapy = types.ModuleType("kaapanapy")
    kaapanapy.helper = fake_helper
    monkeypatch.setitem(sys.modules, "kaapanapy", kaapanapy)
    monkeypatch.setitem(sys.modules, "kaapanapy.helper", fake_helper)
    monkeypatch.setattr("sys.argv", ["upload_to_data_api.py", "-i", str(channel)])
    # Run-context present so we get past the guard to the manifest check.
    monkeypatch.setenv("KAAPANA_DAG_ID", "dag")
    monkeypatch.setenv("KAAPANA_WORKFLOW_RUN_ID", "run")
    with pytest.raises(RuntimeError, match="upload_manifest"):
        mod.main()
