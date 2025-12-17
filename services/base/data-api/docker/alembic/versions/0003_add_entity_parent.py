"""Add parent-child relationship for data entities

Revision ID: 0003_add_entity_parent
Revises: 0002_add_data_entity_created_at
Create Date: 2025-11-29 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_add_entity_parent"
down_revision = "0002_add_data_entity_created_at"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("data_entities", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_data_entities_parent",
        "data_entities",
        "data_entities",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_data_entities_parent_id", "data_entities", ["parent_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_data_entities_parent_id", table_name="data_entities")
    op.drop_constraint("fk_data_entities_parent", "data_entities", type_="foreignkey")
    op.drop_column("data_entities", "parent_id")
