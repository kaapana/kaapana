"""ship the platform `model` metadata schema

Revision ID: 0004_model_schema
Revises: 0003_provenance_schema
Create Date: 2026-06-01 00:00:00.000000

Registers the platform-shipped ``model`` metadata schema so it is present on
every install.
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0004_model_schema"
down_revision = "0003_provenance_schema"
branch_labels = None
depends_on = None

_MODEL_KEY = "model"

_MODEL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "title": "Model",
    "description": "Describes a trained/fine-tunable AI model entity (permissive in v1).",
    "properties": {
        "name": {"type": "string", "title": "Model name"},
        "framework": {"type": "string", "title": "Framework"},
        "trained_from_scratch": {"type": "boolean", "title": "From scratch"},
    },
    "additionalProperties": True,
}


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO metadata_schemas (key, schema) "
            "VALUES (:key, CAST(:schema AS jsonb)) "
            "ON CONFLICT (key) DO NOTHING"
        ).bindparams(key=_MODEL_KEY, schema=json.dumps(_MODEL_SCHEMA))
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM metadata_schemas WHERE key = :key").bindparams(
            key=_MODEL_KEY
        )
    )
