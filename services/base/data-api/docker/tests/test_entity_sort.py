from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql

from app.models.query import QueryRequest, SortSpec
from app.services.entity_query import (
    DataEntityORM,
    QueryTranslationError,
    _keyset_after,
    _metadata_sort_subquery,
    _parse_metadata_field,
    _schema_path_is_numeric,
)

_CURSOR = UUID("12345678-1234-5678-1234-567812345678")


def _sql(clause) -> str:
    return str(
        clause.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    ).lower()


# ---- SortSpec / QueryRequest defaults ------------------------------------


def test_sortspec_direction_defaults_to_asc() -> None:
    assert SortSpec(field="created_at").direction == "asc"


def test_sortspec_rejects_unknown_direction() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SortSpec(field="created_at", direction="sideways")


def test_query_request_sort_defaults_to_none() -> None:
    assert QueryRequest().sort is None


# ---- schema-driven numeric detection -------------------------------------


def test_schema_path_numeric_for_declared_number() -> None:
    schema = {"properties": {"score": {"type": "number"}}}
    assert _schema_path_is_numeric(schema, ("score",)) is True


def test_schema_path_numeric_for_declared_integer() -> None:
    schema = {"properties": {"epochs": {"type": "integer"}}}
    assert _schema_path_is_numeric(schema, ("epochs",)) is True


def test_schema_path_text_for_string_and_permissive() -> None:
    schema = {"properties": {"name": {"type": "string"}}}
    assert _schema_path_is_numeric(schema, ("name",)) is False
    # permissive schema (no properties)  text fallback
    assert _schema_path_is_numeric({"additionalProperties": True}, ("x",)) is False
    assert _schema_path_is_numeric(None, ("x",)) is False


def test_schema_path_walks_nested_properties() -> None:
    schema = {"properties": {"metrics": {"properties": {"auc": {"type": "number"}}}}}
    assert _schema_path_is_numeric(schema, ("metrics", "auc")) is True
    assert _schema_path_is_numeric(schema, ("metrics", "missing")) is False


# ---- metadata sort expression --------------------------------------------


def test_metadata_sort_subquery_text_path() -> None:
    field = _parse_metadata_field("metadata.model-card.name")
    sql = _sql(_metadata_sort_subquery(field, numeric=False))
    assert "model-card" in sql
    assert "name" in sql
    assert "cast" not in sql  # text path: no numeric cast


def test_metadata_sort_subquery_numeric_path_casts() -> None:
    field = _parse_metadata_field("metadata.model-card.score")
    sql = _sql(_metadata_sort_subquery(field, numeric=True))
    assert "cast" in sql
    assert "numeric" in sql


# ---- keyset (NULLS LAST, id tiebreak) ------------------------------------


def test_keyset_after_asc_non_null_cursor() -> None:
    sql = _sql(_keyset_after(DataEntityORM.created_at, "asc", "2024-01-01", _CURSOR))
    # later value OR nulls-after OR same-value/later-id
    assert "created_at >" in sql
    assert "is null" in sql
    assert "id >" in sql


def test_keyset_after_desc_non_null_cursor() -> None:
    sql = _sql(_keyset_after(DataEntityORM.created_at, "desc", "2024-01-01", _CURSOR))
    assert "created_at <" in sql
    assert "is null" in sql


def test_keyset_after_null_cursor_pages_within_null_tail() -> None:
    sql = _sql(_keyset_after(DataEntityORM.created_at, "asc", None, _CURSOR))
    # in the NULL tail we only continue by id among nulls
    assert "is null" in sql
    assert "id >" in sql
    assert "created_at >" not in sql


def test_resolve_sort_expression_rejects_unknown_field() -> None:
    import asyncio

    from app.services.entity_query import _resolve_sort_expression

    with pytest.raises(QueryTranslationError):
        asyncio.run(_resolve_sort_expression(None, SortSpec(field="storage.type")))
