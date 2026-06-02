from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql

from app.models.query import FilterNode, QueryOp

from app.services.entity_query import (
    QueryTranslationError,
    _build_filter_predicate,
    _build_metadata_predicate,
    _coerce_bool,
    _coerce_link_type,
    _coerce_link_value,
    _coerce_uuid,
    _normalize_storage_type,
    _parse_metadata_field,
    _sequence_from_value,
)


def _sql(clause) -> str:
    """Compile a SQLAlchemy clause to a literal SQL string for assertions."""
    return str(
        clause.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    ).lower()


def test_parse_metadata_field_requires_key() -> None:
    with pytest.raises(QueryTranslationError):
        _parse_metadata_field("metadata.")


def test_parse_metadata_field_parses_path_segments() -> None:
    parsed = _parse_metadata_field("metadata.acquisition.details.series")
    assert parsed.key == "acquisition"
    assert parsed.path == ("details", "series")


def test_coerce_uuid_accepts_string_values() -> None:
    raw = "12345678-1234-5678-1234-567812345678"
    value = _coerce_uuid(raw)
    assert isinstance(value, UUID)
    assert str(value) == raw


def test_coerce_uuid_rejects_invalid_strings() -> None:
    with pytest.raises(QueryTranslationError):
        _coerce_uuid("not-a-uuid")


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("true", True),
        ("FALSE", False),
        ("1", True),
        ("0", False),
    ],
)
def test_coerce_bool_normalizes_common_strings(raw: str, expected: bool) -> None:
    assert _coerce_bool(raw) is expected


def test_normalize_storage_type_lowercases_and_trims() -> None:
    assert _normalize_storage_type("  S3  ") == "s3"


def test_sequence_from_value_handles_scalars_and_lists() -> None:
    assert _sequence_from_value("abc") == ["abc"]
    assert _sequence_from_value([1, 2]) == [1, 2]
    assert _sequence_from_value(None) == []


def test_has_key_builds_presence_exists_without_value() -> None:
    clause = _build_metadata_predicate(
        _parse_metadata_field("metadata.model-card"), QueryOp.HAS_KEY, None
    )
    sql = _sql(clause)
    # Presence check: an EXISTS keyed on the metadata key, with no value comparison
    # and no JSON traversal of the data column.
    assert "exists" in sql
    assert "model-card" in sql
    assert "->" not in sql
    assert ".data" not in sql


def test_has_key_ignores_field_path() -> None:
    with_path = _sql(
        _build_metadata_predicate(
            _parse_metadata_field("metadata.model-card.metrics"),
            QueryOp.HAS_KEY,
            None,
        )
    )
    # field.path is ignored for key-level presence: no traversal, no path segment.
    assert "->" not in with_path
    assert "metrics" not in with_path
    assert "model-card" in with_path


def test_has_key_routes_through_filter_predicate_without_value() -> None:
    # FilterNode.value is optional, so a presence filter needs no operand.
    node = FilterNode(field="metadata.model-card", op=QueryOp.HAS_KEY)
    sql = _sql(_build_filter_predicate(node))
    assert "exists" in sql
    assert "model-card" in sql


def test_coerce_link_value_returns_uuid_and_normalized_type() -> None:
    raw = "12345678-1234-5678-1234-567812345678"
    entity_id, link_type = _coerce_link_value(
        {"entity_id": raw, "link_type": " Contains "}
    )
    assert entity_id == UUID(raw)
    assert link_type == "contains"


@pytest.mark.parametrize(
    "value",
    [
        "not-a-dict",
        {"entity_id": "12345678-1234-5678-1234-567812345678"},
        {"link_type": "contains"},
        {"entity_id": "bad", "link_type": "contains"},
    ],
)
def test_coerce_link_value_rejects_bad_shapes(value: object) -> None:
    with pytest.raises(QueryTranslationError):
        _coerce_link_value(value)


def test_coerce_link_type_accepts_string_and_dict() -> None:
    assert _coerce_link_type("Contains") == "contains"
    assert _coerce_link_type({"link_type": "FOO"}) == "foo"


@pytest.mark.parametrize("value", ["", "   ", 42, {}, {"link_type": ""}])
def test_coerce_link_type_rejects_invalid(value: object) -> None:
    with pytest.raises(QueryTranslationError):
        _coerce_link_type(value)


def test_eq_on_nested_metadata_path_builds_json_value_comparison() -> None:
    # Dataset find-or-create (incoming-DICOM DAG) relies on eq matching a nested
    # metadata path: metadata.dataset.name == "<name>". This must traverse the
    # JSON data column and compare the value as a JSONB literal, not degrade to a
    # presence check (has_key) or raise QueryTranslationError.
    # Compiled WITHOUT literal_binds: a JSONB literal can't be rendered inline, but
    # it binds and executes fine at runtime — the structure is what we assert here.
    node = FilterNode(field="metadata.dataset.name", op=QueryOp.EQ, value="cohort-a")
    sql = str(
        _build_filter_predicate(node).compile(dialect=postgresql.dialect())
    ).lower()
    assert "exists" in sql
    assert ".data ->" in sql  # JSON traversal into the .name path segment
    assert "::jsonb" in sql  # value compared as a JSONB literal, not presence-only
