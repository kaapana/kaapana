"""Add cleanup columns to workflow_runs

Revision ID: 8f4a2c1eaab1
Revises: 721d0352a128
Create Date: 2026-05-29 12:00:00.000000

Adds policy-driven cleanup support for workflow runs (issue #2202).

The cleanup_policy server_default is intentionally NEVER even though the
Pydantic default on WorkflowRunCreate is ON_SUCCESS: rows that pre-exist
this migration include runs that were submitted before opt-in existed,
and they must not be retroactively cleaned. Only newly-submitted runs,
which traverse the Pydantic layer, pick up the ON_SUCCESS default.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f4a2c1eaab1"
down_revision: Union[str, None] = "721d0352a128"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


cleanup_policy_enum = sa.Enum("NEVER", "ON_SUCCESS", "ALWAYS", name="cleanuppolicy")
cleanup_status_enum = sa.Enum(
    "NOT_REQUIRED", "PENDING", "RUNNING", "CLEANED", "FAILED", name="cleanupstatus"
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    cleanup_policy_enum.create(bind, checkfirst=True)
    cleanup_status_enum.create(bind, checkfirst=True)

    op.add_column(
        "workflow_runs",
        sa.Column(
            "cleanup_policy",
            cleanup_policy_enum,
            nullable=False,
            server_default="NEVER",
        ),
    )
    op.add_column(
        "workflow_runs",
        sa.Column(
            "cleanup_status",
            cleanup_status_enum,
            nullable=False,
            server_default="NOT_REQUIRED",
        ),
    )
    op.add_column(
        "workflow_runs",
        sa.Column("cleaned_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("workflow_runs", "cleaned_at")
    op.drop_column("workflow_runs", "cleanup_status")
    op.drop_column("workflow_runs", "cleanup_policy")

    bind = op.get_bind()
    cleanup_status_enum.drop(bind, checkfirst=True)
    cleanup_policy_enum.drop(bind, checkfirst=True)
