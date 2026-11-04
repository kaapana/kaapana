"""v0-8-0 keep detached extensions and record uploaded ones

Revision ID: 0a8ad08f71cb
Revises: fde3423414cf
Create Date: 2026-10-06 14:00:00.000000

Deleting a repository sets repository_id to NULL on its extensions instead of
deleting them, so installed extensions can still be uninstalled. The downgrade
fails while such detached extensions exist.

Uploaded extensions have no repository either. The origin column tells them
apart from detached ones, and existing extensions came from a repository. The
reason column explains the current status, for example why an installation
failed.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0a8ad08f71cb"
down_revision: Union[str, None] = "fde3423414cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EXTENSION_ORIGIN = sa.Enum("repository", "upload", name="extension_origin")


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

    EXTENSION_ORIGIN.create(op.get_bind(), checkfirst=True)
    with op.batch_alter_table("extensions") as batch_op:
        batch_op.add_column(
            sa.Column("origin", EXTENSION_ORIGIN, nullable=False, server_default="repository"),
        )
        batch_op.add_column(sa.Column("uploaded_by", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("uploaded_filename", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("reason", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("extensions") as batch_op:
        batch_op.drop_column("reason")
        batch_op.drop_column("uploaded_filename")
        batch_op.drop_column("uploaded_by")
        batch_op.drop_column("origin")
    EXTENSION_ORIGIN.drop(op.get_bind(), checkfirst=True)

    _set_repository_fk(nullable=False, ondelete="CASCADE")
