"""Add creation timestamp to data entities

Revision ID: 0002_add_data_entity_created_at
Revises: 0001_initial
Create Date: 2025-11-29 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_data_entity_created_at"
down_revision = "0001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "data_entities",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_data_entities_created_at", "data_entities", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_data_entities_created_at", table_name="data_entities")
    op.drop_column("data_entities", "created_at")
