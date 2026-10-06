"""v0-8-0 keep extensions when their repository is removed

Revision ID: 0a8ad08f71cb
Revises: fde3423414cf
Create Date: 2026-10-06 14:00:00.000000

Deleting a repository sets repository_id to NULL on its extensions instead of
deleting them, so installed extensions can still be uninstalled. The downgrade
fails while such detached extensions exist.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0a8ad08f71cb"
down_revision: Union[str, None] = "fde3423414cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _set_repository_fk(nullable: bool, ondelete: str) -> None:
    with op.batch_alter_table("extensions") as batch_op:
        batch_op.drop_constraint("extensions_repository_id_fkey", type_="foreignkey")
        batch_op.alter_column("repository_id", existing_type=postgresql.UUID(as_uuid=True), nullable=nullable)
        batch_op.create_foreign_key(
            "extensions_repository_id_fkey",
            "registries",
            ["repository_id"],
            ["id"],
            ondelete=ondelete,
        )


def upgrade() -> None:
    """Upgrade schema."""
    _set_repository_fk(nullable=True, ondelete="SET NULL")


def downgrade() -> None:
    """Downgrade schema."""
    _set_repository_fk(nullable=False, ondelete="CASCADE")
