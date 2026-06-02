"""ship the platform `dataset` metadata schema

Revision ID: 0005_dataset_schema
Revises: 0004_model_schema
Create Date: 2026-06-02 00:00:00.000000

Registers the platform-shipped ``dataset`` metadata schema so it is present on
every install.
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0005_dataset_schema"
down_revision = "0004_model_schema"
branch_labels = None
depends_on = None

_DATASET_KEY = "dataset"

_DATASET_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "title": "Dataset",
    "description": "Marks an entity as a dataset; members are attached via 'contains' links.",
    "properties": {
        "name": {
            "type": "string",
            "title": "Dataset name",
            "description": "Human-readable name of the dataset.",
        },
    },
    "required": ["name"],
    "additionalProperties": True,
}


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO metadata_schemas (key, schema) "
            "VALUES (:key, CAST(:schema AS jsonb)) "
            "ON CONFLICT (key) DO NOTHING"
        ).bindparams(key=_DATASET_KEY, schema=json.dumps(_DATASET_SCHEMA))
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM metadata_schemas WHERE key = :key").bindparams(
            key=_DATASET_KEY
        )
    )
