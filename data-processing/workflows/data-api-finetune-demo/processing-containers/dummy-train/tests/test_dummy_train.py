"""Unit tests for the dummy fine-tune task.

The module is loaded by path so importing it needs no kaapanapy runtime. The
tests build two fake input channels (one per-entity subdir each) and assert the
task summarises both, writes its manifest + dummy model, and fails loudly on an
empty channel.
"""

import importlib.util
import json
import pathlib

import pytest

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "files" / "dummy_train.py"


def _load():
    spec = importlib.util.spec_from_file_location("dummy_train_standalone", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_channel(root: pathlib.Path, entities: dict) -> pathlib.Path:
    root.mkdir(parents=True, exist_ok=True)
    for entity_id, files in entities.items():
        entity_dir = root / entity_id
        entity_dir.mkdir()
        for name, content in files.items():
            (entity_dir / name).write_text(content)
    return root


def test_inspect_channel_lists_entities(tmp_path):
    mod = _load()
    root = _make_channel(tmp_path / "seg", {"e1": {"a.dcm": "x"}, "e2": {"b.dcm": "y"}})
    summary = mod._inspect_channel("segmentations", root)
    assert {s["entity_id"] for s in summary} == {"e1", "e2"}
    assert summary[0]["files"]  # non-empty file list


def test_inspect_channel_empty_fails(tmp_path):
    mod = _load()
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(RuntimeError):
        mod._inspect_channel("model", empty)


def test_inspect_channel_missing_mount_fails(tmp_path):
    mod = _load()
    with pytest.raises(RuntimeError):
        mod._inspect_channel("model", tmp_path / "does-not-exist")


def test_inspect_channel_allow_empty_returns_empty(tmp_path):
    mod = _load()
    empty = tmp_path / "empty"
    empty.mkdir()
    assert mod._inspect_channel("model", empty, allow_empty=True) == []
    # Missing mount is also tolerated when allow_empty.
    assert mod._inspect_channel("model", tmp_path / "nope", allow_empty=True) == []


def test_main_writes_outputs(tmp_path, monkeypatch):
    mod = _load()
    seg = _make_channel(tmp_path / "seg", {"s1": {"seg.dcm": "x"}})
    model = _make_channel(tmp_path / "model", {"m1": {"weights.bin": "w"}})
    out = tmp_path / "out"

    monkeypatch.setattr(
        "sys.argv",
        [
            "dummy_train.py",
            "--segmentations",
            str(seg),
            "--model",
            str(model),
            "-o",
            str(out),
        ],
    )
    mod.main()

    manifest = json.loads((out / "training_manifest.json").read_text())
    assert manifest["trained"] is False
    assert manifest["from_scratch"] is False
    assert {e["entity_id"] for e in manifest["segmentations"]} == {"s1"}
    assert {e["entity_id"] for e in manifest["base_model"]} == {"m1"}
    assert (out / "model.dummy").is_file()

    # The upload manifest tells data-api-upload what entity to create.
    upload = json.loads((out / "upload_manifest.json").read_text())
    assert upload["store"] == "s3"
    assert upload["metadata"]["model"]["trained_from_scratch"] is False
    assert upload["metadata"]["model"]["base_model_entity_ids"] == ["m1"]
    # The workflow's own key, registered by the ensure_schema task.
    assert upload["metadata"]["finetune-note"]["reviewed"] is False
    # Lineage = segmentation inputs + the base model.
    assert set(upload["upstream_entity_ids"]) == {"s1", "m1"}


def test_main_from_scratch_with_empty_model_channel(tmp_path, monkeypatch):
    mod = _load()
    seg = _make_channel(tmp_path / "seg", {"s1": {"seg.dcm": "x"}})
    empty_model = tmp_path / "model"
    empty_model.mkdir()  # present but empty -> train from scratch
    out = tmp_path / "out"

    monkeypatch.setattr(
        "sys.argv",
        [
            "dummy_train.py",
            "--segmentations",
            str(seg),
            "--model",
            str(empty_model),
            "-o",
            str(out),
        ],
    )
    mod.main()

    manifest = json.loads((out / "training_manifest.json").read_text())
    assert manifest["from_scratch"] is True
    assert manifest["base_model"] == []

    upload = json.loads((out / "upload_manifest.json").read_text())
    assert upload["metadata"]["model"]["trained_from_scratch"] is True
    assert upload["metadata"]["model"]["base_model_entity_ids"] == []
    # No base model -> lineage is just the segmentation inputs.
    assert upload["upstream_entity_ids"] == ["s1"]
