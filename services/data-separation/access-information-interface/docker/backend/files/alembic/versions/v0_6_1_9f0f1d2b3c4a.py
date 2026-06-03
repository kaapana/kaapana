"""v0-6-1

Revision ID: 9f0f1d2b3c4a
Revises: 6d23c430c44c
Create Date: 2026-03-12 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f0f1d2b3c4a"
down_revision: Union[str, None] = "6d23c430c44c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "projects",
        sa.Column(
            "multiinstallable_whitelist",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("projects", "multiinstallable_whitelist")
