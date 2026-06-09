"""add kind column to installed_models

Revision ID: a1b2c3d4e5f6
Revises: fa8abfc02de3
Create Date: 2026-06-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "beab7a9f4fad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE installed_models ADD COLUMN IF NOT EXISTS kind VARCHAR(50) DEFAULT 'nnunet'"
    )


def downgrade() -> None:
    op.drop_column("installed_models", "kind")
