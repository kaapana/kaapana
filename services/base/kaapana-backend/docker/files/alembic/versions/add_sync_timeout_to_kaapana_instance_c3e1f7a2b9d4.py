"""add sync_timeout column to kaapana_instance

Revision ID: c3e1f7a2b9d4
Revises: a1b2c3d4e5f6
Create Date: 2026-10-06

"""

from typing import Sequence, Union

from alembic import op

revision: str = "c3e1f7a2b9d4"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE kaapana_instance ADD COLUMN IF NOT EXISTS sync_timeout INTEGER NOT NULL DEFAULT 15")


def downgrade() -> None:
    op.drop_column("kaapana_instance", "sync_timeout")
