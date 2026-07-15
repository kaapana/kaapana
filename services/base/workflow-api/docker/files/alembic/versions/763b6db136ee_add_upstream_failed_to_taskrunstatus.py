"""Add UPSTREAM_FAILED to taskrunstatus enum

Revision ID: 763b6db136ee
Revises: 8f4a2c1eaab1
Create Date: 2026-07-03 12:00:00.000000

The taskrunstatus enum was created in the initial migration without the
UPSTREAM_FAILED value (issue #2258). The value was later added in Python
(schemas.TaskRunStatus, Airflow adapter mapping upstream_failed ->
UPSTREAM_FAILED) but never in the database, so persisting an upstream-failed
task raised "invalid input value for enum taskrunstatus".

PostgreSQL does not allow ALTER TYPE ... ADD VALUE inside a transaction
block, so the statement runs in an autocommit block. ADD VALUE cannot be
reverted, hence downgrade is a no-op.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "763b6db136ee"
down_revision: Union[str, None] = "8f4a2c1eaab1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE taskrunstatus ADD VALUE IF NOT EXISTS 'UPSTREAM_FAILED'")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL cannot remove a value from an enum type; nothing to undo.
    pass
