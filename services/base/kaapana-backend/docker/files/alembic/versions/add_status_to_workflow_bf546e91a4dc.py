"""add status column to workflow

Revision ID: bf546e91a4dc
Revises: a1b2c3d4e5f6
Create Date: 2026-09-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "bf546e91a4dc"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Transient workflow-level state ("queuing", "aborting", "deleting"), NULL when
    # idle. IF NOT EXISTS so a database that already carries the column (created by
    # a build that shipped this migration under another revision id) starts instead
    # of crash-looping on a duplicate-column error.
    op.execute("ALTER TABLE workflow ADD COLUMN IF NOT EXISTS status VARCHAR(64)")


def downgrade() -> None:
    op.drop_column("workflow", "status")
