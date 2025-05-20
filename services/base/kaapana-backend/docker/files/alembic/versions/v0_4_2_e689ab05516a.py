"""v0-4-2

Revision ID: e689ab05516a
Revises: 5d694eb1a7b1
Create Date: 2025-04-15 16:45:06.641749

"""

import os
from typing import Sequence, Union

import requests
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "e689ab05516a"
down_revision: Union[str, None] = "5d694eb1a7b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def fetch_project_id_uuid_mapping():
    aii_service = os.environ["ACCESS_INFORMATION_INTERFACE_URL"]
    response = requests.get(f"{aii_service}/projects")
    projects = response.json()

    return {project["int_id"]: project["id"] for project in projects}


def fetch_uuid_to_project_id_mapping():
    id_uuid_map = fetch_project_id_uuid_mapping()
    return {uuid: pid for pid, uuid in id_uuid_map.items()}


def upgrade() -> None:
    id_uuid_map = fetch_project_id_uuid_mapping()

    connection = op.get_bind()
    op.drop_constraint("dataset_project_id_name_key", "dataset", type_="unique")
    op.alter_column("dataset", "project_id", new_column_name="old_project_id")
    op.alter_column("workflow", "project_id", new_column_name="old_project_id")

    op.add_column("dataset", sa.Column("project_id", UUID(), nullable=True))
    op.add_column("workflow", sa.Column("project_id", UUID(), nullable=True))
    op.create_unique_constraint(None, "dataset", ["project_id", "name"])

    # Update existing records using the map
    for old_id, new_uuid in id_uuid_map.items():
        if old_id:
            connection.execute(
                sa.text(
                    """
                        UPDATE dataset SET project_id = :uuid WHERE old_project_id = :old_id
                    """
                ),
                {"uuid": new_uuid, "old_id": old_id},
            )
            connection.execute(
                sa.text(
                    """
                    UPDATE workflow SET project_id = :uuid WHERE old_project_id = :old_id
                """
                ),
                {"uuid": new_uuid, "old_id": old_id},
            )

    op.alter_column("dataset", "project_id", nullable=False)
    op.alter_column("workflow", "project_id", nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    connection = op.get_bind()

    # Add project_id column back as nullable
    op.add_column("dataset", sa.Column("project_id", sa.Integer(), nullable=True))
    op.add_column("workflow", sa.Column("project_id", sa.Integer(), nullable=True))

    # Fetch reverse mapping UUID -> ID
    uuid_id_map = fetch_uuid_to_project_id_mapping()

    for uuid, project_id in uuid_id_map.items():
        connection.execute(
            sa.text("UPDATE dataset SET project_id = :pid WHERE project_id = :uuid"),
            {"pid": project_id, "uuid": uuid},
        )
        connection.execute(
            sa.text("UPDATE workflow SET project_id = :pid WHERE project_id = :uuid"),
            {"pid": project_id, "uuid": uuid},
        )

    # Make project_id mandatory again
    op.alter_column("dataset", "project_id", nullable=False)
    op.alter_column("workflow", "project_id", nullable=False)

    # Restore old constraint
    op.drop_constraint(None, "dataset", type_="unique")
    op.create_unique_constraint(
        "dataset_project_id_name_key", "dataset", ["project_id", "name"]
    )

    # Drop project_id column
    op.drop_column("workflow", "project_id")
    op.drop_column("dataset", "project_id")
