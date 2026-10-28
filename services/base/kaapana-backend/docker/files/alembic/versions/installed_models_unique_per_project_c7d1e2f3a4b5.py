"""installed_models.friendly_name unique per project and kind instead of globally

Revision ID: c7d1e2f3a4b5
Revises: a1b2c3d4e5f6
Create Date: 2026-10-27

"""

from typing import Sequence, Union

from alembic import op

revision: str = "c7d1e2f3a4b5"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE installed_models DROP CONSTRAINT IF EXISTS installed_models_friendly_name_key")
    op.create_unique_constraint(
        "uq_installed_models_project_kind_name", "installed_models", ["project_id", "kind", "friendly_name"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_installed_models_project_kind_name", "installed_models", type_="unique")
    op.create_unique_constraint("installed_models_friendly_name_key", "installed_models", ["friendly_name"])
