"""ship the platform `provenance` metadata schema

Revision ID: 0003_provenance_schema
Revises: 0002_entity_links
Create Date: 2026-05-31 00:00:00.000000

Registers the platform-shipped ``provenance`` metadata schema so it is present
on every install.
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0003_provenance_schema"
down_revision = "0002_entity_links"
branch_labels = None
depends_on = None

_PROVENANCE_KEY = "provenance"

_PROVENANCE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "title": "Provenance",
    "description": (
        "Execution context that produced this entity (workflow/run/task/image, "
        "project, time) plus the upstream entity IDs it derived from."
    ),
    "properties": {
        "workflow_name": {
            "type": "string",
            "description": "Producing workflow identifier (Airflow dag_id).",
        },
        "workflow_run_id": {
            "type": "string",
            "description": "Producing workflow run identifier (Airflow run_id).",
        },
        "task_id": {"type": "string", "description": "Producing task identifier."},
        "image": {"type": "string", "description": "Producing operator image."},
        "produced_at": {
            "type": "string",
            "format": "date-time",
            "description": "ISO-8601 timestamp the entity was produced.",
        },
        "project": {"type": "string", "description": "Owning project identifier."},
        "upstream_entity_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Entity IDs this entity was derived from (lineage).",
        },
    },
    "additionalProperties": True,
}


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO metadata_schemas (key, schema) "
            "VALUES (:key, CAST(:schema AS jsonb)) "
            "ON CONFLICT (key) DO NOTHING"
        ).bindparams(key=_PROVENANCE_KEY, schema=json.dumps(_PROVENANCE_SCHEMA))
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM metadata_schemas WHERE key = :key").bindparams(
            key=_PROVENANCE_KEY
        )
    )
