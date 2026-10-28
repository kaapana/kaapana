"""installed_models.form_defaults: further workflow form fields an entry fills in

Revision ID: d8e2f3a4b5c6
Revises: c7d1e2f3a4b5
Create Date: 2026-10-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d8e2f3a4b5c6"
down_revision: Union[str, None] = "c7d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "installed_models",
        sa.Column("form_defaults", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("installed_models", "form_defaults")
