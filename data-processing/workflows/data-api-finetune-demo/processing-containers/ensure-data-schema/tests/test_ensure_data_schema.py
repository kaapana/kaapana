"""Unit tests for the ensure-data-schema task.

The module imports ``data_api`` at top and ``kaapanapy`` lazily inside ``_amain``.
We stub both in ``sys.modules`` before loading by path, then assert the schema is
well-formed and that ``_amain`` registers it under the expected key.
"""

import asyncio
import importlib.util
import json
import pathlib
import sys
import types

MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "files" / "ensure_data_schema.py"
)


class _FakeData:
    def __init__(self, *a, **k):
        self.registered = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def register_metadata_schema(self, key, schema):
        self.registered.append((key, schema))


def _load():
    # Stub data_api so the top-level import succeeds without the base image.
    data_api = types.ModuleType("data_api")
    data_api.DataClient = _FakeData
    sys.modules["data_api"] = data_api

    spec = importlib.util.spec_from_file_location(
        "ensure_data_schema_standalone", MODULE_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_schema_is_json_serialisable_object():
    mod = _load()
    schema = mod.FINETUNE_NOTE_SCHEMA
    assert json.loads(json.dumps(schema)) == schema
    assert schema["type"] == "object"
    assert schema["$schema"].endswith("draft-07/schema#")
    # Permissive so the demo can attach arbitrary note fields.
    assert schema["additionalProperties"] is True
    assert set(schema["properties"]) >= {"note", "reviewed"}


def test_amain_registers_under_finetune_note_key(monkeypatch):
    mod = _load()

    fake_data = _FakeData()
    monkeypatch.setattr(mod, "DataClient", lambda *a, **k: fake_data)

    fake_helper = types.ModuleType("kaapanapy.helper")
    fake_helper.get_project_user_access_token = lambda: "tok"
    kaapanapy = types.ModuleType("kaapanapy")
    kaapanapy.helper = fake_helper
    monkeypatch.setitem(sys.modules, "kaapanapy", kaapanapy)
    monkeypatch.setitem(sys.modules, "kaapanapy.helper", fake_helper)

    asyncio.run(mod._amain())

    assert fake_data.registered == [(mod.FINETUNE_NOTE_KEY, mod.FINETUNE_NOTE_SCHEMA)]
    assert mod.FINETUNE_NOTE_KEY == "finetune-note"
