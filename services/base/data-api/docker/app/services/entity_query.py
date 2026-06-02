from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    and_,
    Select,
    cast,
    exists,
    false,
    func,
    literal,
    or_,
    select,
    true,
    tuple_,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.types import Boolean, Numeric, Text

from app.db.models import (
    DataEntityORM,
    MetadataEntryORM,
    StorageCoordinateORM,
    MetadataSchemaORM,
)
from app.models.domain import DataEntity
from app.models.query import (
    FilterNode,
    GroupNode,
    QueryIndexRequest,
    QueryNode,
    QueryOp,
    QueryRequest,
)
from app.config import get_settings
from app.services import entity_repository


@dataclass(frozen=True)
class ParsedMetadataField:
    key: str
    path: tuple[str, ...]


class QueryTranslationError(Exception):
    """Raised when a QueryRequest cannot be represented with SQL filters."""


class SortResultTooLarge(Exception):
    """A metadata-path sort would sort more rows than ``MAX_SORT_RESULT_SIZE``.

    Index-backed sorts (created_at / id) are never raised; only the in-memory
    JSONB-path sort is capped to protect the DB on broad-constraint queries.
    """


async def execute_entity_query(
    session: AsyncSession,
    request: QueryRequest,
) -> tuple[list[DataEntity], int, UUID | None]:
    predicate = _build_query_predicate(request.where)
    total_count = await _count_entities(session, predicate)

    limit = request.limit or 100
    stmt = entity_repository._entity_select()
    if predicate is not None:
        stmt = stmt.where(predicate)

    if request.sort is not None:
        stmt = await _apply_sorted_page(session, stmt, request, total_count, limit)
    else:
        stmt = stmt.order_by(*entity_repository._creation_order()).limit(limit + 1)
        if request.cursor:
            created_at, cursor_id = await entity_repository._cursor_tuple(
                session, request.cursor
            )
            stmt = stmt.where(
                tuple_(DataEntityORM.created_at, DataEntityORM.id)
                > tuple_(created_at, cursor_id)
            )

    result = await session.execute(stmt)
    rows = result.scalars().unique().all()
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = page[-1].id if has_more and page else None
    return entity_repository.entities_from_orms(page), total_count, next_cursor


async def find_one_matching(
    session: AsyncSession, where: QueryNode | None
) -> DataEntity | None:
    """Return the first entity matching ``where``, or ``None``.

    A single ``LIMIT 1`` scan with no count or pagination — the cheap existence
    check the ``/entities/ensure`` get-or-create path needs (it must not pay for
    ``execute_entity_query``'s ``_count_entities`` full scan). Raises
    ``QueryTranslationError`` / ``ValueError`` for unsupported filters, exactly
    like the paged query path.
    """
    predicate = _build_query_predicate(where)
    stmt = entity_repository._entity_select()
    if predicate is not None:
        stmt = stmt.where(predicate)
    stmt = stmt.limit(1)
    result = await session.execute(stmt)
    row = result.scalars().unique().first()
    return entity_repository.entity_from_orm(row) if row is not None else None


async def prepare_query_index_statement(
    session: AsyncSession,
    request: QueryIndexRequest,
) -> tuple[int, Any]:
    predicate = _build_query_predicate(request.where)
    total_count = await _count_entities(session, predicate)

    stmt = (
        select(DataEntityORM.id)
        .order_by(*entity_repository._creation_order())
        .execution_options(stream_results=True)
    )
    if predicate is not None:
        stmt = stmt.where(predicate)

    if request.cursor:
        created_at, cursor_id = await entity_repository._cursor_tuple(
            session, request.cursor
        )
        stmt = stmt.where(
            tuple_(DataEntityORM.created_at, DataEntityORM.id)
            > tuple_(created_at, cursor_id)
        )

    return total_count, stmt


# ---- generic sort --------------------------------------------------------
# Keyset preserved (never offset): the cursor stays a UUID; the cursor's sort
# value is resolved server-side from that ID so pagination works for any key.

_SORT_NUMERIC_TYPES = {"number", "integer"}


async def _apply_sorted_page(
    session: AsyncSession,
    stmt: Select,
    request: QueryRequest,
    total_count: int,
    limit: int,
) -> Select:
    sort = request.sort
    field = (sort.field or "").strip()
    sort_expr = await _resolve_sort_expression(session, sort)

    # Cap only metadata-path sorts: they have no value index and sort the matched
    # set in memory. created_at / id ride their index — cheap at any size.
    if field.startswith("metadata."):
        cap = get_settings().MAX_SORT_RESULT_SIZE
        if total_count > cap:
            raise SortResultTooLarge(
                f"Sorting by '{field}' would order {total_count} rows; the cap is "
                f"{cap}. Narrow the query, or sort by created_at."
            )

    ordered = sort_expr.desc() if sort.direction == "desc" else sort_expr.asc()
    stmt = stmt.order_by(ordered.nulls_last(), DataEntityORM.id.asc()).limit(limit + 1)
    if request.cursor:
        cursor_value = await _resolve_sort_value(session, sort_expr, request.cursor)
        stmt = stmt.where(
            _keyset_after(sort_expr, sort.direction, cursor_value, request.cursor)
        )
    return stmt


async def _resolve_sort_expression(session: AsyncSession, sort: "SortSpec"):
    """Build the orderable SQL expression for a sort field.

    ``created_at`` / ``id`` are entity columns. A ``metadata.<key>[.path]`` field
    becomes a correlated scalar subquery extracting the value (≤1 row, since
    (entity_id, key) is unique in app code), cast to the schema-declared type
    (numeric/integer → Numeric so 10 sorts after 9; else text)."""
    field = (sort.field or "").strip()
    if field in ("", "created_at"):
        return DataEntityORM.created_at
    if field == "id":
        return DataEntityORM.id
    if field.startswith("metadata."):
        parsed = _parse_metadata_field(field)
        numeric = await _metadata_sort_is_numeric(session, parsed.key, parsed.path)
        return _metadata_sort_subquery(parsed, numeric)
    raise QueryTranslationError(f"Unsupported sort field '{field}'")


def _metadata_sort_subquery(field: ParsedMetadataField, numeric: bool):
    """Correlated scalar subquery yielding the entity's value at this metadata
    path (≤1 row, since (entity_id, key) is unique in app code). Numeric paths
    are cast so 10 sorts after 9; everything else sorts as text."""
    json_expr = MetadataEntryORM.data
    for segment in field.path:
        json_expr = json_expr[segment]
    text_expr = json_expr.astext
    value_expr = cast(text_expr, Numeric) if numeric else text_expr
    return (
        select(value_expr)
        .where(
            MetadataEntryORM.entity_id == DataEntityORM.id,
            MetadataEntryORM.key == field.key,
        )
        .scalar_subquery()
    )


async def _metadata_sort_is_numeric(
    session: AsyncSession, key: str, path: tuple[str, ...]
) -> bool:
    result = await session.execute(
        select(MetadataSchemaORM.schema).where(MetadataSchemaORM.key == key)
    )
    return _schema_path_is_numeric(result.scalar_one_or_none(), path)


def _schema_path_is_numeric(schema: Any, path: tuple[str, ...]) -> bool:
    """True when the registered schema declares this path number/integer.

    Falls back to False (text sort) for a permissive/unknown schema."""
    node = schema
    for segment in path:
        if not isinstance(node, dict):
            return False
        node = node.get("properties", {}).get(segment)
    declared = node.get("type") if isinstance(node, dict) else None
    return declared in _SORT_NUMERIC_TYPES


def _keyset_after(
    sort_expr, direction: str, cursor_value: Any, cursor_id: UUID
) -> ColumnElement[bool]:
    """Rows strictly after (cursor_value, cursor_id) in the sort order.

    Ordering is ``sort_expr <dir> NULLS LAST, id ASC``. NULLs sort after every
    non-null value, so once the cursor lands in the NULL tail we page within it
    by id."""
    id_col = DataEntityORM.id
    if cursor_value is None:
        return and_(sort_expr.is_(None), id_col > cursor_id)
    primary = (
        sort_expr < cursor_value if direction == "desc" else sort_expr > cursor_value
    )
    return or_(
        primary,
        sort_expr.is_(None),
        and_(sort_expr == cursor_value, id_col > cursor_id),
    )


async def _resolve_sort_value(session: AsyncSession, sort_expr, cursor_id: UUID) -> Any:
    result = await session.execute(
        select(sort_expr).where(DataEntityORM.id == cursor_id)
    )
    row = result.one_or_none()
    if row is None:
        raise ValueError("Cursor ID not found")
    return row[0]


async def _count_entities(
    session: AsyncSession, predicate: ColumnElement[bool] | None
) -> int:
    stmt = select(func.count(DataEntityORM.id))
    if predicate is not None:
        stmt = stmt.where(predicate)
    result = await session.execute(stmt)
    scalar = result.scalar_one()
    return int(scalar or 0)


def _build_query_predicate(node: QueryNode | None) -> ColumnElement[bool] | None:
    if node is None:
        return None
    if isinstance(node, FilterNode):
        return _build_filter_predicate(node)
    return _build_group_predicate(node)


def _build_group_predicate(node: GroupNode) -> ColumnElement[bool] | None:
    clauses = [
        clause
        for child in node.children
        if (clause := _build_query_predicate(child)) is not None
    ]
    if not clauses:
        return None
    if node.op == "and":
        return and_(*clauses)
    return or_(*clauses)


def _build_filter_predicate(node: FilterNode) -> ColumnElement[bool]:
    field = (node.field or "").strip()
    if field == "id":
        return _build_id_predicate(node.op, node.value)
    if field == "storage.any":
        return _build_storage_any_predicate(node.op, node.value)
    if field == "storage.type":
        return _build_storage_type_predicate(node.op, node.value)
    if field.startswith("metadata."):
        parsed = _parse_metadata_field(field)
        return _build_metadata_predicate(parsed, node.op, node.value)
    raise QueryTranslationError(f"Unsupported query field '{field}'")


def _build_id_predicate(op: QueryOp, value: Any) -> ColumnElement[bool]:
    column = DataEntityORM.id
    if op is QueryOp.EQ:
        return column == _coerce_uuid(value)
    if op is QueryOp.LT:
        return column < _coerce_uuid(value)
    if op is QueryOp.LTE:
        return column <= _coerce_uuid(value)
    if op is QueryOp.GT:
        return column > _coerce_uuid(value)
    if op is QueryOp.GTE:
        return column >= _coerce_uuid(value)
    if op is QueryOp.IN:
        uuids = _coerce_uuid_list(value)
        if not uuids:
            return false()
        return column.in_(uuids)
    if op is QueryOp.NOT_IN:
        uuids = _coerce_uuid_list(value)
        if not uuids:
            return true()
        return ~column.in_(uuids)

    text_column = cast(column, Text)
    token = _string_value(value)
    if op is QueryOp.CONTAINS:
        return text_column.contains(token)
    if op is QueryOp.NOT_CONTAINS:
        return ~text_column.contains(token)
    if op is QueryOp.STARTS_WITH:
        return text_column.startswith(token)
    if op is QueryOp.ENDS_WITH:
        return text_column.endswith(token)
    raise QueryTranslationError(f"Operator '{op}' is not supported for field 'id'")


def _build_storage_any_predicate(op: QueryOp, value: Any) -> ColumnElement[bool]:
    storage_exists = exists(
        select(1).where(StorageCoordinateORM.entity_id == DataEntityORM.id)
    )
    if op is QueryOp.EQ:
        return storage_exists if _coerce_bool(value) else ~storage_exists
    if op is QueryOp.IN:
        bools = [_coerce_bool(item) for item in _sequence_from_value(value)]
        if not bools:
            return false()
        clauses = [storage_exists if flag else ~storage_exists for flag in bools]
        return or_(*clauses)
    if op is QueryOp.NOT_IN:
        bools = [_coerce_bool(item) for item in _sequence_from_value(value)]
        if not bools:
            return true()
        clauses = [~storage_exists if flag else storage_exists for flag in bools]
        return and_(*clauses)
    if op in {QueryOp.LT, QueryOp.LTE, QueryOp.GT, QueryOp.GTE}:
        numeric_value = _coerce_numeric(value)
        numeric_expr = cast(storage_exists, Numeric)
        return _numeric_compare(numeric_expr, numeric_value, op)
    if op in {
        QueryOp.CONTAINS,
        QueryOp.NOT_CONTAINS,
        QueryOp.STARTS_WITH,
        QueryOp.ENDS_WITH,
    }:
        return false()
    raise QueryTranslationError(
        f"Operator '{op}' is not supported for field 'storage.any'"
    )


def _build_storage_type_predicate(op: QueryOp, value: Any) -> ColumnElement[bool]:
    if op is QueryOp.NOT_IN:
        values = [_normalize_storage_type(item) for item in _sequence_from_value(value)]
        if not values:
            return true()
        storage_alias = aliased(StorageCoordinateORM)
        stmt = select(1).where(
            storage_alias.entity_id == DataEntityORM.id,
            storage_alias.type.in_(values),
        )
        return ~exists(stmt)

    if op in {QueryOp.IN, QueryOp.CONTAINS}:
        values = [_normalize_storage_type(item) for item in _sequence_from_value(value)]
        if not values:
            return false()
        storage_alias = aliased(StorageCoordinateORM)
        stmt = select(1).where(
            storage_alias.entity_id == DataEntityORM.id,
            storage_alias.type.in_(values),
        )
        return exists(stmt)

    if op is QueryOp.EQ:
        normalized = _normalize_storage_type(value)
        storage_alias = aliased(StorageCoordinateORM)
        stmt = select(1).where(
            storage_alias.entity_id == DataEntityORM.id,
            storage_alias.type == normalized,
        )
        return exists(stmt)

    if op is QueryOp.STARTS_WITH:
        tokens = [_normalize_storage_type(item) for item in _sequence_from_value(value)]
        if not tokens:
            return false()
        clauses = []
        for token in tokens:
            storage_alias = aliased(StorageCoordinateORM)
            stmt = select(1).where(
                storage_alias.entity_id == DataEntityORM.id,
                storage_alias.type.startswith(token),
            )
            clauses.append(exists(stmt))
        return or_(*clauses)

    if op is QueryOp.ENDS_WITH:
        tokens = [_normalize_storage_type(item) for item in _sequence_from_value(value)]
        if not tokens:
            return false()
        clauses = []
        for token in tokens:
            storage_alias = aliased(StorageCoordinateORM)
            stmt = select(1).where(
                storage_alias.entity_id == DataEntityORM.id,
                storage_alias.type.endswith(token),
            )
            clauses.append(exists(stmt))
        return or_(*clauses)

    if op is QueryOp.NOT_CONTAINS:
        tokens = [_normalize_storage_type(item) for item in _sequence_from_value(value)]
        if not tokens:
            return true()
        storage_alias = aliased(StorageCoordinateORM)
        stmt = select(1).where(
            storage_alias.entity_id == DataEntityORM.id,
            storage_alias.type.in_(tokens),
        )
        return ~exists(stmt)

    raise QueryTranslationError(
        f"Operator '{op}' is not supported for field 'storage.type'"
    )


def _build_metadata_predicate(
    field: ParsedMetadataField, op: QueryOp, value: Any
) -> ColumnElement[bool]:
    metadata_alias = aliased(MetadataEntryORM)
    if op is QueryOp.HAS_KEY:
        return exists(
            select(1).where(
                metadata_alias.entity_id == DataEntityORM.id,
                metadata_alias.key == field.key,
            )
        )
    stmt = select(1).where(
        metadata_alias.entity_id == DataEntityORM.id,
        metadata_alias.key == field.key,
    )
    json_expr = metadata_alias.data
    for segment in field.path:
        json_expr = json_expr[segment]
    comparison = _apply_metadata_operator(json_expr, op, value)
    stmt = stmt.where(comparison)
    return exists(stmt)


def _apply_metadata_operator(json_expr, op: QueryOp, value: Any) -> ColumnElement[bool]:
    if op is QueryOp.EQ:
        return _metadata_eq_expr(json_expr, value)
    if op is QueryOp.IN:
        return _metadata_in_expr(json_expr, value)
    if op is QueryOp.NOT_IN:
        return _metadata_not_in_expr(json_expr, value)
    if op in {QueryOp.LT, QueryOp.LTE, QueryOp.GT, QueryOp.GTE}:
        return _metadata_comparison_expr(json_expr, op, value)
    if op is QueryOp.CONTAINS:
        return _metadata_contains_expr(json_expr, value)
    if op is QueryOp.NOT_CONTAINS:
        return _metadata_not_contains_expr(json_expr, value)
    if op in {QueryOp.STARTS_WITH, QueryOp.ENDS_WITH}:
        return _metadata_string_match_expr(json_expr, op, value)
    raise QueryTranslationError(
        f"Operator '{op}' is not supported for metadata filters"
    )


def _metadata_eq_expr(json_expr, value: Any) -> ColumnElement[bool]:
    if value is None:
        return json_expr.is_(None)
    return json_expr == _json_literal(value)


def _metadata_in_expr(json_expr, value: Any) -> ColumnElement[bool]:
    items = _sequence_from_value(value)
    if not items:
        return false()
    clauses: list[ColumnElement[bool]] = []
    for item in items:
        if item is None:
            clauses.append(json_expr.is_(None))
        else:
            clauses.append(json_expr == _json_literal(item))
    return or_(*clauses)


def _metadata_not_in_expr(json_expr, value: Any) -> ColumnElement[bool]:
    items = _sequence_from_value(value)
    if not items:
        return true()
    clauses: list[ColumnElement[bool]] = []
    for item in items:
        if item is None:
            clauses.append(json_expr.is_(None))
        else:
            clauses.append(json_expr == _json_literal(item))
    return ~or_(*clauses)


def _metadata_comparison_expr(
    json_expr, op: QueryOp, value: Any
) -> ColumnElement[bool]:
    if isinstance(value, bool):
        guard = func.jsonb_typeof(json_expr) == literal("boolean")
        numeric_expr = cast(cast(json_expr.astext, Boolean), Numeric)
        target = 1.0 if value else 0.0
        return and_(guard, _numeric_compare(numeric_expr, target, op))

    if isinstance(value, (int, float)):
        numeric_expr = cast(json_expr.astext, Numeric)
        guard = func.jsonb_typeof(json_expr) == literal("number")
        return and_(guard, _numeric_compare(numeric_expr, float(value), op))

    if isinstance(value, str):
        guard = func.jsonb_typeof(json_expr) == literal("string")
        text_expr = json_expr.astext
        return and_(
            guard,
            _string_compare(text_expr, value, op),
        )
    raise QueryTranslationError(
        "Comparison operators require numeric or string values for metadata fields"
    )


def _metadata_contains_expr(json_expr, value: Any) -> ColumnElement[bool]:
    tokens = _sequence_from_value(value)
    if not tokens:
        return false()
    clauses: list[ColumnElement[bool]] = []
    for token in tokens:
        normalized = _normalize_json_value(token)
        array_clause = and_(
            func.jsonb_typeof(json_expr) == literal("array"),
            json_expr.contains(_json_literal([normalized])),
        )
        string_clause = and_(
            func.jsonb_typeof(json_expr) == literal("string"),
            json_expr.astext.contains(str(normalized)),
        )
        clauses.append(or_(array_clause, string_clause))
    return or_(*clauses)


def _metadata_not_contains_expr(json_expr, value: Any) -> ColumnElement[bool]:
    tokens = _sequence_from_value(value)
    if not tokens:
        return true()
    clauses: list[ColumnElement[bool]] = []
    for token in tokens:
        normalized = _normalize_json_value(token)
        array_clause = and_(
            func.jsonb_typeof(json_expr) == literal("array"),
            ~json_expr.contains(_json_literal([normalized])),
        )
        string_clause = and_(
            func.jsonb_typeof(json_expr) == literal("string"),
            ~json_expr.astext.contains(str(normalized)),
        )
        clauses.append(or_(array_clause, string_clause))
    return and_(*clauses)


def _metadata_string_match_expr(
    json_expr, op: QueryOp, value: Any
) -> ColumnElement[bool]:
    token = _string_value(value)
    guard = func.jsonb_typeof(json_expr) == literal("string")
    text_expr = json_expr.astext
    if op is QueryOp.STARTS_WITH:
        return and_(guard, text_expr.startswith(token))
    return and_(guard, text_expr.endswith(token))


def _parse_metadata_field(field: str) -> ParsedMetadataField:
    parts = field.split(".")
    if len(parts) < 2 or not parts[1]:
        raise QueryTranslationError("Metadata filters must specify a metadata key")
    key = parts[1]
    path = tuple(segment for segment in parts[2:] if segment)
    return ParsedMetadataField(key=key, path=path)


def _coerce_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError as exc:
            raise QueryTranslationError("Invalid UUID value in query filter") from exc
    raise QueryTranslationError("ID filters require UUID values")


def _coerce_uuid_list(value: Any) -> list[UUID]:
    return [_coerce_uuid(item) for item in _sequence_from_value(value)]


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    raise QueryTranslationError("Boolean filters expect values like true/false")


def _coerce_numeric(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    raise QueryTranslationError("Numeric comparison requires an int or float value")


def _numeric_compare(
    expr: ColumnElement[Any], target: float, op: QueryOp
) -> ColumnElement[bool]:
    if op is QueryOp.LT:
        return expr < target
    if op is QueryOp.LTE:
        return expr <= target
    if op is QueryOp.GT:
        return expr > target
    if op is QueryOp.GTE:
        return expr >= target
    raise QueryTranslationError("Unsupported numeric comparison operator")


def _string_compare(
    expr: ColumnElement[Any], target: str, op: QueryOp
) -> ColumnElement[bool]:
    if op is QueryOp.LT:
        return expr < target
    if op is QueryOp.LTE:
        return expr <= target
    if op is QueryOp.GT:
        return expr > target
    if op is QueryOp.GTE:
        return expr >= target
    raise QueryTranslationError("Unsupported string comparison operator")


def _sequence_from_value(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _normalize_storage_type(value: Any) -> str:
    token = _string_value(value).strip().lower()
    if not token:
        raise QueryTranslationError("Storage type filters require a non-empty value")
    return token


def _json_literal(value: Any):
    normalized = _normalize_json_value(value)
    return literal(normalized, type_=JSONB)


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _normalize_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_json_value(v) for v in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _string_value(value: Any) -> str:
    if value is None:
        raise QueryTranslationError("String comparison requires a non-null value")
    return str(value)
