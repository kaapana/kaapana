"""v0-6-1

Revision ID: 9f0f1d2b3c4a
Revises: 6e751c62ecfa
Create Date: 2026-03-12 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f0f1d2b3c4a"
down_revision: Union[str, None] = "6e751c62ecfa"
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
    op.create_table(
        "multiinstallable_blacklist",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("app_name", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("app_name"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("multiinstallable_blacklist")
    op.drop_column("projects", "multiinstallable_whitelist")
