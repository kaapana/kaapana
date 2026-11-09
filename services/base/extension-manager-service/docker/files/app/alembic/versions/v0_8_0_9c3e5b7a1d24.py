"""v0-8-0 extension updates

Revision ID: 9c3e5b7a1d24
Revises: 4ea93663b83a
Create Date: 2026-11-09 18:00:00.000000

Adds the target of a running update to extensions, the version each content last received
and the update statuses.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c3e5b7a1d24"
down_revision: Union[str, None] = "4ea93663b83a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("extensions", sa.Column("pending_update", sa.JSON(), nullable=True))
    op.add_column("contents", sa.Column("applied_version", sa.String(length=64), nullable=True))
    op.execute(
        "UPDATE contents SET applied_version = extensions.manifest ->> 'version' "
        "FROM extensions WHERE contents.extension_id = extensions.id AND contents.status = 'installed'"
    )
    for enum_name in ("extension_status", "content_status"):
        for value in ("updating", "update_failed"):
            op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL cannot drop enum values, so the update statuses stay in the types.
    op.drop_column("contents", "applied_version")
    op.drop_column("extensions", "pending_update")
