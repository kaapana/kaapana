"""Rename extension label keys

Revision ID: a3b6e8a2a074
Revises: 763b6db136ee
Create Date: 2026-11-03 12:00:00.000000

An extension update replaces the workflow with a new revision, so the
extension's name and version must be allowed to change. They lose the
kaapana.immutable. prefix; the workflow_name key becomes content_name.
Labels are shared rows referenced by revisions and runs, so renaming the
key on the labels table covers both.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b6e8a2a074"
down_revision: Union[str, None] = "763b6db136ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RENAMES = [
    ("kaapana.immutable.extension.version", "kaapana.extension.version"),
    ("kaapana.immutable.extension.name", "kaapana.extension.name"),
    ("kaapana.immutable.extension.workflow_name", "kaapana.immutable.extension.content_name"),
]


def _rename(old: str, new: str) -> None:
    op.execute(sa.text("UPDATE labels SET key = :new WHERE key = :old").bindparams(old=old, new=new))


def upgrade() -> None:
    """Upgrade schema."""
    for old, new in RENAMES:
        _rename(old, new)


def downgrade() -> None:
    """Downgrade schema."""
    for old, new in RENAMES:
        _rename(new, old)
