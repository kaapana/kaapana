"""v0-8-0 detached extensions

Revision ID: 625fa3ea38a8
Revises: 9c3e5b7a1d24
Create Date: 2026-11-19 12:00:00.000000

Removing a repository keeps its extensions: repository_id becomes nullable with
ON DELETE SET NULL, and each extension stores the name and URL of its repository.
The downgrade deletes the records of detached extensions. Their content stays on the platform.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "625fa3ea38a8"
down_revision: Union[str, None] = "9c3e5b7a1d24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _set_repository_fk(nullable: bool, ondelete: str) -> None:
    op.drop_constraint("extensions_repository_id_fkey", "extensions", type_="foreignkey")
    op.alter_column("extensions", "repository_id", existing_type=postgresql.UUID(as_uuid=True), nullable=nullable)
    op.create_foreign_key(
        "extensions_repository_id_fkey",
        "extensions",
        "registries",
        ["repository_id"],
        ["id"],
        ondelete=ondelete,
    )


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("extensions", sa.Column("repository_name", sa.String(length=255), nullable=True))
    op.add_column("extensions", sa.Column("repository_url", sa.String(length=2048), nullable=True))
    op.execute(
        sa.text(
            "UPDATE extensions SET repository_name = registries.name, repository_url = registries.repository_url "
            "FROM registries WHERE extensions.repository_id = registries.id"
        )
    )
    op.alter_column("extensions", "repository_name", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("extensions", "repository_url", existing_type=sa.String(length=2048), nullable=False)
    _set_repository_fk(nullable=True, ondelete="SET NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("DELETE FROM extensions WHERE repository_id IS NULL"))
    _set_repository_fk(nullable=False, ondelete="CASCADE")
    op.drop_column("extensions", "repository_url")
    op.drop_column("extensions", "repository_name")
