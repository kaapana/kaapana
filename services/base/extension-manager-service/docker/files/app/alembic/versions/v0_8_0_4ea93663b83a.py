"""v0-8-0 upload repository and detached extensions

Revision ID: 4ea93663b83a
Revises: fde3423414cf
Create Date: 2026-11-09 12:00:00.000000

Adds the built-in Upload repository that holds extensions installed from a file.
Removing a repository keeps its extensions: repository_id becomes nullable with
ON DELETE SET NULL, and each extension stores the name and URL of its repository.
The downgrade deletes the records of detached extensions.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4ea93663b83a"
down_revision: Union[str, None] = "fde3423414cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UPLOAD_REPOSITORY_ID = "8f49216f-786c-42ba-9413-0722e781ea28"


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
    op.add_column("extensions", sa.Column("repository_name", sa.String(length=255), nullable=True))
    op.add_column("extensions", sa.Column("repository_url", sa.String(length=2048), nullable=True))
    op.execute(
        sa.text(
            "UPDATE extensions SET repository_name = registries.name, repository_url = registries.repository_url "
            "FROM registries WHERE extensions.repository_id = registries.id"
        )
    )
    with op.batch_alter_table("extensions") as batch_op:
        batch_op.alter_column("repository_name", existing_type=sa.String(length=255), nullable=False)
        batch_op.alter_column("repository_url", existing_type=sa.String(length=2048), nullable=False)
    _set_repository_fk(nullable=True, ondelete="SET NULL")
    op.execute(
        sa.text(
            "UPDATE registries SET name = name || ' (renamed)' WHERE name = 'Upload' AND id <> CAST(:id AS uuid)"
        ).bindparams(id=UPLOAD_REPOSITORY_ID)
    )
    op.execute(
        sa.text(
            "INSERT INTO registries (id, name, description, repository_url, authentication) "
            "VALUES (CAST(:id AS uuid), 'Upload', 'Extensions installed from a file.', 'upload://local', '')"
        ).bindparams(id=UPLOAD_REPOSITORY_ID)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("DELETE FROM extensions WHERE repository_id IS NULL"))
    _set_repository_fk(nullable=False, ondelete="CASCADE")
    op.drop_column("extensions", "repository_url")
    op.drop_column("extensions", "repository_name")
    op.execute(sa.text("DELETE FROM registries WHERE id = CAST(:id AS uuid)").bindparams(id=UPLOAD_REPOSITORY_ID))
