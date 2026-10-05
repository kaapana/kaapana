from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from app.db.models import DataEntityORM, MetadataEntryORM, MetadataSchemaORM
from app.models.domain import DataEntity, MetadataEntry
from fastapi import HTTPException, Request
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

PERMISSIONS_KEY = "permissions"

PERMISSIONS_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "title": "Permissions",
    "description": "Permissions and project associations for the entity",
    "properties": {
        "project": {"type": "string", "description": "Project ID that owns this entity"},
        "owner": {"type": ["string", "null"], "description": "Owner of the entity, null by default"},
    },
    "additionalProperties": True,
}


@dataclass(frozen=True)
class ProjectScope:
    id: str


class InvalidProjectHeader(ValueError):
    pass


def parse_project_header(header: str | None) -> ProjectScope | None:
    if not header:
        return None
    try:
        project = json.loads(header)
    except ValueError as exc:
        raise InvalidProjectHeader("Invalid Project header") from exc
    project_id = project.get("id") if isinstance(project, dict) else None
    if not isinstance(project_id, str) or not project_id:
        raise InvalidProjectHeader("Invalid Project header")
    return ProjectScope(id=project_id)


def get_project_scope(request: Request) -> ProjectScope | None:
    try:
        return parse_project_header(request.headers.get("Project"))
    except InvalidProjectHeader as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def entity_in_project(project_id: str, entity_id_column: Any = DataEntityORM.id) -> ColumnElement[bool]:
    permissions = aliased(MetadataEntryORM)
    return exists(
        select(1).where(
            permissions.entity_id == entity_id_column,
            permissions.key == PERMISSIONS_KEY,
            permissions.data.contains({"project": project_id}),
        )
    )


def scope_predicate(scope: ProjectScope | None, entity_id_column: Any = DataEntityORM.id) -> ColumnElement[bool] | None:
    if scope is None:
        return None
    return entity_in_project(scope.id, entity_id_column)


def _project_of_entries(entries: Iterable[MetadataEntryORM | MetadataEntry]) -> str | None:
    for entry in entries:
        if entry.key != PERMISSIONS_KEY or not isinstance(entry.data, dict):
            continue
        project = entry.data.get("project")
        return project if isinstance(project, str) else None
    return None


def project_of_entity(entity: DataEntityORM | DataEntity) -> str | None:
    if isinstance(entity, DataEntityORM):
        return _project_of_entries(entity.metadata_entries)
    return _project_of_entries(entity.metadata)


def ensure_in_scope(entity: DataEntityORM, scope: ProjectScope | None) -> None:
    if scope is not None and project_of_entity(entity) != scope.id:
        raise HTTPException(status_code=404, detail="Entity not found")


def assign_entity_to_scope(entity: DataEntity, scope: ProjectScope) -> DataEntity:
    entries = [entry for entry in entity.metadata if entry.key == PERMISSIONS_KEY]
    if not entries:
        permissions = MetadataEntry(key=PERMISSIONS_KEY, data={"project": scope.id, "owner": None})
        return entity.model_copy(update={"metadata": [*entity.metadata, permissions]})
    if any(entry.data.get("project") != scope.id for entry in entries):
        raise HTTPException(status_code=403, detail="The entity is assigned to a different project")
    return entity


def guard_permissions_change(key: str, data: dict[str, Any] | None, scope: ProjectScope | None) -> None:
    if scope is None or key != PERMISSIONS_KEY:
        return
    if data is None:
        raise HTTPException(
            status_code=403,
            detail="The permissions entry cannot be removed while working in a project",
        )
    if data.get("project") != scope.id:
        raise HTTPException(
            status_code=403,
            detail="The permissions entry cannot move the entity to a different project",
        )


async def ensure_permissions_schema(db: AsyncSession) -> None:
    result = await db.execute(select(MetadataSchemaORM.id).where(MetadataSchemaORM.key == PERMISSIONS_KEY))
    if result.scalar_one_or_none() is None:
        db.add(MetadataSchemaORM(key=PERMISSIONS_KEY, schema=PERMISSIONS_SCHEMA))
