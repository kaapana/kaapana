"""

Revision ID: 6d23c430c44c
Revises: 6e751c62ecfa
Create Date: 2026-04-17 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6d23c430c44c"
down_revision: Union[str, None] = "6e751c62ecfa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "projects",
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute(
        "ALTER TABLE projects "
        "DROP CONSTRAINT IF EXISTS projects_kubernetes_namespace_key, "
        "DROP CONSTRAINT IF EXISTS projects_s3_bucket_key, "
        "DROP CONSTRAINT IF EXISTS projects_opensearch_index_key, "
        "DROP COLUMN IF EXISTS kubernetes_namespace, "
        "DROP COLUMN IF EXISTS s3_bucket, "
        "DROP COLUMN IF EXISTS opensearch_index;"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "projects", sa.Column("kubernetes_namespace", sa.String(), nullable=True)
    )
    op.add_column("projects", sa.Column("s3_bucket", sa.String(), nullable=True))
    op.add_column(
        "projects", sa.Column("opensearch_index", sa.String(), nullable=True)
    )
    op.create_unique_constraint(
        "projects_kubernetes_namespace_key", "projects", ["kubernetes_namespace"]
    )
    op.create_unique_constraint(
        "projects_s3_bucket_key", "projects", ["s3_bucket"]
    )
    op.create_unique_constraint(
        "projects_opensearch_index_key", "projects", ["opensearch_index"]
    )
    op.drop_column("projects", "is_archived")
