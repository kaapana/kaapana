"""v0-7-0 initial

Revision ID: fde3423414cf
Revises:
Create Date: 2026-10-06 14:00:00.000000

The schema as Base.metadata.create_all built it in 0.7.0. Databases created
before Alembic are stamped with this revision by migrate.py.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "fde3423414cf"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EXTENSION_STATUS = sa.Enum(
    "pending",
    "pulling",
    "pulling_failed",
    "installing",
    "installing_failed",
    "installed",
    "uninstalling",
    "uninstalled",
    "uninstalling_failed",
    name="extension_status",
)
CONTENT_STATUS = sa.Enum(
    "pending",
    "installing",
    "installation_failed",
    "installed",
    "uninstalling",
    "uninstallation_failed",
    "uninstalled",
    name="content_status",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "registries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("repository_url", sa.String(length=2048), nullable=False),
        sa.Column("authentication", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="registries_pkey"),
        sa.UniqueConstraint("name", name="registries_name_key"),
    )
    op.create_table(
        "extensions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag", sa.String(length=128), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("status", EXTENSION_STATUS, server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["registries.id"],
            name="extensions_repository_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="extensions_pkey"),
        sa.UniqueConstraint("repository_id", "tag", name="uq_repository_id_tag"),
    )
    op.create_table(
        "contents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extension_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("status", CONTENT_STATUS, server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["extension_id"],
            ["extensions.id"],
            name="contents_extension_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="contents_pkey"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("contents")
    op.drop_table("extensions")
    op.drop_table("registries")
    CONTENT_STATUS.drop(op.get_bind(), checkfirst=True)
    EXTENSION_STATUS.drop(op.get_bind(), checkfirst=True)
