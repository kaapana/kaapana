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


def _prep(mod, tmp_path, monkeypatch, *, manifest):
    channel = tmp_path / "results"
    channel.mkdir()
    (channel / "model.dummy").write_text("weights")
    (channel / "upload_manifest.json").write_text(json.dumps(manifest))

    storage, data = _FakeStorage(), _FakeData()
    monkeypatch.setattr(mod, "StorageClient", lambda *a, **k: storage)
    monkeypatch.setattr(mod, "DataClient", lambda *a, **k: data)

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
    "metadata": {"model-card": {"name": "dummy", "trained_from_scratch": True}},
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
    # "proj" is not a UUID, so it is treated as a short_id/name and prefixed.
    assert call["target"]["bucket"] == "project-proj"
    assert call["target"]["key_prefix"].startswith(
        "data-api/models/data-api-finetune-demo_v1/run-7/"
    )
    assert [name for name, _ in call["files"]] == ["model.dummy"]

    # Minted an entity with the returned coordinate.
    assert data.created["storage_coordinates"][0]["type"] == "s3"
    new_id = data.created["id"]

    attached = {key: value for (eid, key, value) in data.attached if eid == new_id}
    # model-card came from the manifest.
    assert attached["model-card"]["name"] == "dummy"
    # provenance came from the trusted run-context env, NOT the manifest.
    prov = attached["provenance"]
    assert prov["workflow_name"] == "data-api-finetune-demo_v1"
    assert prov["workflow_run_id"] == "run-7"
    assert prov["task_id"] == "upload_model"
    assert prov["project"] == "proj"
    assert prov["upstream_entity_ids"] == ["seg-1", "seg-2"]
    assert "produced_at" in prov


def test_upload_bucket_inferred_from_uuid(tmp_path, monkeypatch):
    # A full project UUID maps to the AII convention "project-{uuid.hex[:8]}".
    mod = _load()
    storage, _ = _prep(mod, tmp_path, monkeypatch, manifest=_MANIFEST)
    monkeypatch.delenv("UPLOAD_S3_BUCKET", raising=False)
    monkeypatch.setenv(
        "KAAPANA_PROJECT_IDENTIFIER", "04b73a5d-dead-beef-0000-000000000000"
    )
    mod.main()
    assert storage.calls[0]["target"]["bucket"] == "project-04b73a5d"


def test_upload_bucket_override_wins(tmp_path, monkeypatch):
    # An explicit UPLOAD_S3_BUCKET override beats the inferred project bucket.
    mod = _load()
    storage, _ = _prep(mod, tmp_path, monkeypatch, manifest=_MANIFEST)
    monkeypatch.setenv("UPLOAD_S3_BUCKET", "explicit-bucket")
    monkeypatch.setenv(
        "KAAPANA_PROJECT_IDENTIFIER", "04b73a5d-dead-beef-0000-000000000000"
    )
    mod.main()
    assert storage.calls[0]["target"]["bucket"] == "explicit-bucket"


def test_upload_bucket_admin_literal(tmp_path, monkeypatch):
    # The admin project's bucket is "project-admin" (not derivable from a UUID).
    mod = _load()
    storage, _ = _prep(mod, tmp_path, monkeypatch, manifest=_MANIFEST)
    monkeypatch.delenv("UPLOAD_S3_BUCKET", raising=False)
    monkeypatch.setenv("KAAPANA_PROJECT_IDENTIFIER", "admin")
    mod.main()
    assert storage.calls[0]["target"]["bucket"] == "project-admin"


def test_upload_bucket_passthrough_when_already_prefixed(tmp_path, monkeypatch):
    # An identifier that is already a "project-…" bucket name is used as-is.
    mod = _load()
    storage, _ = _prep(mod, tmp_path, monkeypatch, manifest=_MANIFEST)
    monkeypatch.delenv("UPLOAD_S3_BUCKET", raising=False)
    monkeypatch.setenv("KAAPANA_PROJECT_IDENTIFIER", "project-04b73a5d")
    mod.main()
    assert storage.calls[0]["target"]["bucket"] == "project-04b73a5d"


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
