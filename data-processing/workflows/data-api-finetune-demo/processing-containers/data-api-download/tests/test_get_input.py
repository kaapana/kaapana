"""Unit test for the download task's constraint re-validation.

Because workflow-api no longer freezes against the Data API, the entity IDs are
client-supplied; the operator re-applies the channel's constraint and must fail
loudly on any ID that violates it (or no longer exists). The module imports
``data_api`` at top (installed in the base image) but only imports kaapanapy
lazily inside ``main``, so it loads here without the kaapanapy runtime.
"""

import asyncio
import importlib.util
import pathlib

import pytest

MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "files" / "get_input_from_data_api.py"
)

CONSTRAINT = {"type": "filter", "field": "metadata.model-card", "op": "has_key"}


def _load():
    spec = importlib.util.spec_from_file_location("get_input_standalone", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeData:
    """Stand-in DataClient whose query_index returns a fixed 'matched' set."""

    def __init__(self, matched):
        self._matched = matched
        self.where = None

    async def query_index(self, where):
        self.where = where
        return self._matched


def test_validate_passes_when_all_ids_satisfy_constraint():
    mod = _load()
    data = _FakeData(matched=["e1", "e2"])
    asyncio.run(mod._validate_constraint(data, ["e1", "e2"], CONSTRAINT))
    # The validation query ANDs the constraint with an `id in [...]` filter.
    assert data.where["op"] == "and"
    ops = {c.get("op") for c in data.where["children"]}
    assert ops == {"has_key", "in"}


def test_validate_fails_loud_when_an_id_violates_constraint():
    mod = _load()
    data = _FakeData(matched=["e1"])  # e2 not returned -> violates / missing
    with pytest.raises(RuntimeError, match="do not satisfy the workflow constraint"):
        asyncio.run(mod._validate_constraint(data, ["e1", "e2"], CONSTRAINT))


def test_cardinality_single_rejects_more_than_one_id():
    mod = _load()
    with pytest.raises(RuntimeError, match="single-cardinality"):
        mod._validate_cardinality(["e1", "e2"], "single")


def test_cardinality_single_allows_zero_or_one():
    mod = _load()
    mod._validate_cardinality([], "single")  # optional single, train from scratch
    mod._validate_cardinality(["e1"], "single")


def test_cardinality_multiple_allows_many():
    mod = _load()
    mod._validate_cardinality(["e1", "e2", "e3"], "multiple")
