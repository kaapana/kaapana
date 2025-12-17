"""Migrate entity identifiers from integers to UUIDs

Revision ID: 0004_migrate_entity_ids_to_uuid
Revises: 0003_add_entity_parent
Create Date: 2025-11-30 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0004_migrate_entity_ids_to_uuid"
down_revision = "0003_add_entity_parent"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


UUID_REGEX = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    op.add_column(
        "data_entities",
        sa.Column(
            "new_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    op.add_column(
        "data_entities",
        sa.Column("new_parent_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.add_column(
        "storage_coordinates",
        sa.Column("new_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "metadata_entries",
        sa.Column("new_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE data_entities
            SET new_id = CASE
                WHEN uid ~* :uuid_regex THEN uid::uuid
                ELSE gen_random_uuid()
            END
            """
        ).bindparams(uuid_regex=UUID_REGEX)
    )

    op.execute(
        """
        UPDATE data_entities AS child
        SET new_parent_id = parent.new_id
        FROM data_entities AS parent
        WHERE child.parent_id = parent.id
        """
    )

    op.execute(
        """
        UPDATE storage_coordinates AS sc
        SET new_entity_id = de.new_id
        FROM data_entities AS de
        WHERE sc.entity_id = de.id
        """
    )

    op.execute(
        """
        UPDATE metadata_entries AS me
        SET new_entity_id = de.new_id
        FROM data_entities AS de
        WHERE me.entity_id = de.id
        """
    )

    op.alter_column("storage_coordinates", "new_entity_id", nullable=False)
    op.alter_column("metadata_entries", "new_entity_id", nullable=False)

    op.drop_constraint(
        "storage_coordinates_entity_id_fkey", "storage_coordinates", type_="foreignkey"
    )
    op.drop_constraint(
        "metadata_entries_entity_id_fkey", "metadata_entries", type_="foreignkey"
    )
    op.drop_constraint("fk_data_entities_parent", "data_entities", type_="foreignkey")

    op.drop_index("ix_storage_coordinates_entity_id", table_name="storage_coordinates")
    op.drop_index("ix_metadata_entries_entity_id", table_name="metadata_entries")
    op.drop_index("ix_data_entities_parent_id", table_name="data_entities")
    op.drop_index("ix_data_entities_uid", table_name="data_entities")

    op.drop_constraint("data_entities_pkey", "data_entities", type_="primary")

    op.alter_column(
        "data_entities",
        "id",
        new_column_name="legacy_int_id",
        existing_type=sa.Integer(),
    )
    op.alter_column(
        "data_entities",
        "parent_id",
        new_column_name="legacy_parent_int_id",
        existing_type=sa.Integer(),
    )
    op.alter_column(
        "storage_coordinates",
        "entity_id",
        new_column_name="legacy_entity_int_id",
        existing_type=sa.Integer(),
    )
    op.alter_column(
        "metadata_entries",
        "entity_id",
        new_column_name="legacy_entity_int_id",
        existing_type=sa.Integer(),
    )

    op.alter_column("data_entities", "new_id", new_column_name="id")
    op.alter_column("data_entities", "new_parent_id", new_column_name="parent_id")
    op.alter_column("storage_coordinates", "new_entity_id", new_column_name="entity_id")
    op.alter_column("metadata_entries", "new_entity_id", new_column_name="entity_id")

    op.drop_column("data_entities", "legacy_int_id")
    op.drop_column("data_entities", "legacy_parent_int_id")
    op.drop_column("storage_coordinates", "legacy_entity_int_id")
    op.drop_column("metadata_entries", "legacy_entity_int_id")
    op.drop_column("data_entities", "uid")

    op.create_primary_key("data_entities_pkey", "data_entities", ["id"])
    op.create_index(
        "ix_data_entities_parent_id", "data_entities", ["parent_id"], unique=False
    )

    op.create_index(
        "ix_storage_coordinates_entity_id",
        "storage_coordinates",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_metadata_entries_entity_id", "metadata_entries", ["entity_id"], unique=False
    )

    op.create_foreign_key(
        "fk_data_entities_parent",
        "data_entities",
        "data_entities",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "storage_coordinates_entity_id_fkey",
        "storage_coordinates",
        "data_entities",
        ["entity_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "metadata_entries_entity_id_fkey",
        "metadata_entries",
        "data_entities",
        ["entity_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    raise RuntimeError("Downgrade from UUID identifiers is not supported")
