"""initial db schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-11-29 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_entities",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("uid", sa.String(length=255), nullable=False),
    )
    op.create_index(op.f("ix_data_entities_uid"), "data_entities", ["uid"], unique=True)

    op.create_table(
        "metadata_schemas",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_index(
        op.f("ix_metadata_schemas_key"), "metadata_schemas", ["key"], unique=True
    )

    op.create_table(
        "storage_coordinates",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "entity_id",
            sa.Integer(),
            sa.ForeignKey("data_entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index(
        op.f("ix_storage_coordinates_entity_id"),
        "storage_coordinates",
        ["entity_id"],
        unique=False,
    )

    op.create_table(
        "metadata_entries",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "entity_id",
            sa.Integer(),
            sa.ForeignKey("data_entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index(
        op.f("ix_metadata_entries_entity_id"),
        "metadata_entries",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metadata_entries_key"), "metadata_entries", ["key"], unique=False
    )

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "metadata_entry_id",
            sa.Integer(),
            sa.ForeignKey("metadata_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_id", sa.String(length=255), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=True),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_artifacts_metadata_entry_id"),
        "artifacts",
        ["metadata_entry_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_artifacts_metadata_entry_id"), table_name="artifacts")
    op.drop_table("artifacts")

    op.drop_index(op.f("ix_metadata_entries_key"), table_name="metadata_entries")
    op.drop_index(op.f("ix_metadata_entries_entity_id"), table_name="metadata_entries")
    op.drop_table("metadata_entries")

    op.drop_index(
        op.f("ix_storage_coordinates_entity_id"), table_name="storage_coordinates"
    )
    op.drop_table("storage_coordinates")

    op.drop_index(op.f("ix_metadata_schemas_key"), table_name="metadata_schemas")
    op.drop_table("metadata_schemas")

    op.drop_index(op.f("ix_data_entities_uid"), table_name="data_entities")
    op.drop_table("data_entities")
