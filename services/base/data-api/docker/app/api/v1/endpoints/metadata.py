from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Literal, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from jsonschema import Draft7Validator, ValidationError, SchemaError
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MetadataEntryORM, MetadataSchemaORM
from app.db.session import get_async_db
from app.models.domain import DataEntity, MetadataEntry
from app.models.events import EventAction
from app.services.entity_repository import metadata_entry_to_orm
from .helpers import (
    broadcast_entity_event,
    broadcast_metadata_key_event,
    cleanup_metadata_artifacts,
    commit_and_return_entity,
    get_metadata_schema,
    get_metadata_schema_optional,
    require_entity,
)

router = APIRouter(tags=["metadata"])


class MetadataFieldInfo(BaseModel):
    key: str
    path: str
    field: str
    value_type: str | None = Field(
        None, description="Primitive JSON type inferred from schema or data"
    )
    source: Literal["schema", "data", "schema+data"]
    description: str | None = None
    occurrences: int | None = Field(
        None, description="Number of sampled metadata entries containing this field"
    )
    example: Any | None = None


class MetadataFieldListResponse(BaseModel):
    key: str
    total_entries: int
    sampled_entries: int
    fields: list[MetadataFieldInfo]


class MetadataFieldValuesResponse(BaseModel):
    key: str
    path: str
    field: str
    value_type: str | None = None
    values: list[Any]
    sampled_entries: int
    matches: int


def _validate_schema_document(schema: dict) -> None:
    try:
        Draft7Validator.check_schema(schema)
    except SchemaError as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid JSON Schema: {exc.message}"
        ) from exc


@router.post(
    "/metadata/keys/{key}", summary="Register or replace a metadata schema by key"
)
async def register_metadata_schema(
    key: str, schema: dict, db: AsyncSession = Depends(get_async_db)
) -> dict:
    _validate_schema_document(schema)
    stmt = select(MetadataSchemaORM).where(MetadataSchemaORM.key == key)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is None:
        db.add(MetadataSchemaORM(key=key, schema=schema))
        is_new = True
    else:
        existing.schema = schema
        is_new = False

    await db.commit()
    await broadcast_metadata_key_event(
        EventAction.CREATED if is_new else EventAction.UPDATED, key, schema
    )
    return {"key": key, "schema": schema}


@router.get("/metadata/keys", summary="List all registered metadata keys")
async def list_metadata_keys(db: AsyncSession = Depends(get_async_db)) -> list[str]:
    result = await db.execute(select(MetadataSchemaORM.key))
    keys = result.scalars().all()
    keys.sort()
    return keys


@router.get("/metadata/keys/{key}", summary="Fetch a metadata schema by key")
async def get_metadata_schema_endpoint(
    key: str, db: AsyncSession = Depends(get_async_db)
) -> dict:
    schema = await get_metadata_schema(db, key)
    return {"key": schema.key, "schema": schema.schema}


@router.delete(
    "/metadata/keys/{key}", status_code=204, summary="Remove a metadata schema by key"
)
async def delete_metadata_schema(
    key: str, db: AsyncSession = Depends(get_async_db)
) -> Response:
    stmt = select(MetadataSchemaORM).where(MetadataSchemaORM.key == key)
    result = await db.execute(stmt)
    schema = result.scalar_one_or_none()
    if schema is None:
        raise HTTPException(status_code=404, detail="Metadata schema not found")

    # Check if any entities are using this metadata key
    usage_count = await db.scalar(
        select(func.count()).where(MetadataEntryORM.key == key)
    )
    if usage_count and usage_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete metadata schema '{key}': it is used by {usage_count} entity/entities",
        )

    await db.delete(schema)
    await db.commit()
    await broadcast_metadata_key_event(EventAction.DELETED, key)
    return Response(status_code=204)


@router.get(
    "/metadata/keys/{key}/fields",
    response_model=MetadataFieldListResponse,
    summary="List metadata fields observed for a key",
)
async def describe_metadata_fields(
    key: str,
    sample_size: int = Query(
        1000, ge=10, le=5000, description="Maximum metadata entries to sample"
    ),
    db: AsyncSession = Depends(get_async_db),
) -> MetadataFieldListResponse:
    total_entries = (
        await db.scalar(select(func.count()).where(MetadataEntryORM.key == key)) or 0
    )
    stmt = (
        select(MetadataEntryORM.data)
        .where(MetadataEntryORM.key == key)
        .limit(sample_size)
    )
    result = await db.execute(stmt)
    payloads = result.scalars().all()
    sampled_entries = len(payloads)

    data_stats = _collect_data_field_stats(payloads)
    schema_record = await get_metadata_schema_optional(db, key)
    schema_fields = (
        _collect_schema_fields(schema_record.schema) if schema_record else {}
    )
    fields = _combine_field_descriptions(key, schema_fields, data_stats)

    return MetadataFieldListResponse(
        key=key,
        total_entries=int(total_entries),
        sampled_entries=sampled_entries,
        fields=fields,
    )


@router.get(
    "/metadata/keys/{key}/field-values",
    response_model=MetadataFieldValuesResponse,
    summary="Sample unique values for a metadata field",
)
async def sample_metadata_field_values(
    key: str,
    path: str = Query(..., description="Dot-delimited path inside the metadata entry"),
    limit: int = Query(25, ge=1, le=100),
    sample_size: int = Query(
        1000, ge=10, le=5000, description="Maximum metadata entries to analyze"
    ),
    db: AsyncSession = Depends(get_async_db),
) -> MetadataFieldValuesResponse:
    normalized_path = path.strip()
    stmt = (
        select(MetadataEntryORM.data)
        .where(MetadataEntryORM.key == key)
        .limit(sample_size)
    )
    result = await db.execute(stmt)
    payloads = result.scalars().all()

    seen_tokens: set[str] = set()
    values: list[Any] = []
    matches = 0
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        value = _resolve_metadata_path(payload, normalized_path)
        if value is None:
            continue
        matches += 1
        if len(values) >= limit:
            continue
        token = _freeze_value(value)
        if token in seen_tokens:
            continue
        seen_tokens.add(token)
        values.append(value)

    schema_record = await get_metadata_schema_optional(db, key)
    schema_fields = (
        _collect_schema_fields(schema_record.schema) if schema_record else {}
    )
    schema_info = schema_fields.get(normalized_path)
    value_type = schema_info.get("value_type") if schema_info else None
    if value_type is None and values:
        inferred = {_infer_value_type(v) for v in values}
        if len(inferred) == 1:
            value_type = next(iter(inferred))
        elif inferred:
            value_type = "mixed"

    return MetadataFieldValuesResponse(
        key=key,
        path=normalized_path,
        field=_field_full_path(key, normalized_path),
        value_type=value_type,
        values=values,
        sampled_entries=len(payloads),
        matches=matches,
    )


@router.post(
    "/entities/{entity_id}/metadata",
    response_model=DataEntity,
    summary="Attach metadata to an entity (schema must be registered first)",
)
async def attach_metadata(
    entity_id: UUID,
    entry: MetadataEntry,
    db: AsyncSession = Depends(get_async_db),
) -> DataEntity:
    schema_record = await get_metadata_schema(db, entry.key)
    validator = Draft7Validator(schema_record.schema)
    try:
        validator.validate(entry.data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=400, detail=f"Metadata entry violates schema: {exc.message}"
        ) from exc
    entity = await require_entity(db, entity_id)
    existing_entry = next(
        (m for m in entity.metadata_entries if m.key == entry.key), None
    )
    replaced_existing = existing_entry is not None
    if replaced_existing:
        entity.metadata_entries.remove(existing_entry)

    entity.metadata_entries.append(metadata_entry_to_orm(entry))
    updated = await commit_and_return_entity(db, entity_id)
    if replaced_existing:
        cleanup_metadata_artifacts(entity_id, entry.key)
    await broadcast_entity_event(EventAction.UPDATED, updated)
    return updated


@router.delete(
    "/entities/{entity_id}/metadata/{key}",
    response_model=DataEntity,
    summary="Delete a metadata entry for an entity",
)
async def delete_metadata_entry(
    entity_id: UUID, key: str, db: AsyncSession = Depends(get_async_db)
) -> DataEntity:
    entity = await require_entity(db, entity_id)
    metadata_entry = next((m for m in entity.metadata_entries if m.key == key), None)
    if metadata_entry is None:
        raise HTTPException(status_code=404, detail="Metadata entry not found")

    entity.metadata_entries.remove(metadata_entry)
    updated = await commit_and_return_entity(db, entity_id)
    cleanup_metadata_artifacts(entity_id, key)
    await broadcast_entity_event(EventAction.UPDATED, updated)
    return updated


# ---------------------------------------------------------------------------
# Internal helpers for metadata field statistics
# ---------------------------------------------------------------------------


def _collect_schema_fields(schema: dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    fields: Dict[str, Dict[str, Any]] = {}

    def _walk(node: dict[str, Any], path: tuple[str, ...]) -> None:
        raw_type = node.get("type")
        schema_type: str | None
        if isinstance(raw_type, list):
            schema_type = next(
                (t for t in raw_type if t != "null"), raw_type[0] if raw_type else None
            )
        else:
            schema_type = raw_type

        description = node.get("description")
        if schema_type == "object":
            properties = node.get("properties") or {}
            if isinstance(properties, dict):
                for child_key, child_schema in properties.items():
                    if isinstance(child_schema, dict):
                        _walk(child_schema, path + (str(child_key),))
            return

        if schema_type in {"array"} and path:
            fields[".".join(path)] = {
                "value_type": "array",
                "description": description,
            }
            return

        if path and schema_type is not None:
            fields[".".join(path)] = {
                "value_type": schema_type,
                "description": description,
            }

    _walk(schema, tuple())
    return fields


def _collect_data_field_stats(
    payloads: Sequence[dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    stats: Dict[str, Dict[str, Any]] = {}
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        for path, value in _flatten_metadata_values(payload):
            info = stats.setdefault(path, {"count": 0, "types": set(), "example": None})
            info["count"] += 1
            info["types"].add(_infer_value_type(value))
            if info["example"] is None:
                info["example"] = value
    return stats


def _flatten_metadata_values(
    payload: Any, prefix: Sequence[str] | None = None
) -> Iterable[tuple[str, Any]]:
    prefix = tuple(prefix or ())
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield from _flatten_metadata_values(value, prefix + (str(key),))
        return

    path = ".".join(prefix)
    if path:
        yield path, payload


def _field_full_path(key: str, path: str) -> str:
    return f"metadata.{key}" + (f".{path}" if path else "")


def _combine_field_descriptions(
    key: str,
    schema_fields: Dict[str, Dict[str, Any]],
    data_stats: Dict[str, Dict[str, Any]],
) -> list[MetadataFieldInfo]:
    paths = set(schema_fields.keys()) | set(data_stats.keys())
    results: list[MetadataFieldInfo] = []
    for path in sorted(paths):
        schema_info = schema_fields.get(path)
        data_info = data_stats.get(path)
        if schema_info and data_info:
            source: Literal["schema", "data", "schema+data"] = "schema+data"
        elif schema_info:
            source = "schema"
        else:
            source = "data"

        value_type = schema_info.get("value_type") if schema_info else None
        if value_type is None and data_info:
            types = data_info.get("types") or set()
            if len(types) == 1:
                value_type = next(iter(types))
            elif types:
                value_type = "mixed"

        occurrences = data_info.get("count") if data_info else None
        example = data_info.get("example") if data_info else None
        description = schema_info.get("description") if schema_info else None
        results.append(
            MetadataFieldInfo(
                key=key,
                path=path,
                field=_field_full_path(key, path),
                value_type=value_type,
                source=source,
                description=description,
                occurrences=occurrences,
                example=example,
            ),
        )
    return results


def _resolve_metadata_path(payload: dict[str, Any], path: str) -> Any:
    if not path:
        return payload
    value: Any = payload
    for part in path.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None
    return value


def _freeze_value(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        return repr(value)


def _infer_value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__
