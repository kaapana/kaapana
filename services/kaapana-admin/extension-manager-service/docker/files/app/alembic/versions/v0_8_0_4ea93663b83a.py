"""v0-8-0 upload repository

Revision ID: 4ea93663b83a
Revises: fde3423414cf
Create Date: 2026-11-09 12:00:00.000000

Adds the built-in Upload repository, the local OCI registry that holds uploaded extensions.
"""

import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4ea93663b83a"
down_revision: Union[str, None] = "fde3423414cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UPLOAD_REPOSITORY_ID = "8f49216f-786c-42ba-9413-0722e781ea28"
UPLOAD_REGISTRY_URL = os.environ.get("UPLOAD_REGISTRY_URL", "http://extension-registry.services.svc:5000/uploads")


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text(
            "UPDATE registries SET name = name || ' (renamed)' WHERE name = 'Upload' AND id <> CAST(:id AS uuid)"
        ).bindparams(id=UPLOAD_REPOSITORY_ID)
    )
    op.execute(
        sa.text(
            "INSERT INTO registries (id, name, description, repository_url, authentication) "
            "VALUES (CAST(:id AS uuid), 'Upload', 'Extensions uploaded from a file.', :url, '')"
        ).bindparams(id=UPLOAD_REPOSITORY_ID, url=UPLOAD_REGISTRY_URL)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("DELETE FROM registries WHERE id = CAST(:id AS uuid)").bindparams(id=UPLOAD_REPOSITORY_ID))
