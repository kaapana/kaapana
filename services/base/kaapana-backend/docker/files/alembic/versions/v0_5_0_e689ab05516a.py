"""v0-5-0

Revision ID: e689ab05516a
Revises: 5d694eb1a7b1
Create Date: 2025-04-15 16:45:06.641749

"""

import os
import uuid
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


def fetch_default_project_id() -> uuid.UUID:
    aii_service = os.environ["ACCESS_INFORMATION_INTERFACE_URL"]
    response = requests.get(f"{aii_service}/projects/admin")
    project = response.json()
    return project["id"]


def upgrade() -> None:
    default_project_id = fetch_default_project_id()

    connection = op.get_bind()
    op.add_column(
        "dataset", sa.Column("id", sa.Integer(), autoincrement=True, nullable=True)
    )
    op.add_column("dataset", sa.Column("project_id", UUID(as_uuid=True), nullable=True))
    op.add_column("workflow", sa.Column("project_id", UUID(), nullable=True))
    op.create_unique_constraint(None, "dataset", ["project_id", "name"])
    op.execute(
        """
            CREATE SEQUENCE dataset_id_seq OWNED BY dataset.id;
            UPDATE dataset SET id = nextval('dataset_id_seq');
            ALTER TABLE dataset ALTER COLUMN id SET DEFAULT nextval('dataset_id_seq');
        """
    )
    connection.execute(
        sa.text(
            """
            UPDATE dataset SET project_id = :default_uuid WHERE project_id IS NULL
            """
        ),
        {"default_uuid": default_project_id},
    )
    connection.execute(
        sa.text(
            """
            UPDATE workflow SET project_id = :default_uuid WHERE project_id IS NULL
            """
        ),
        {"default_uuid": default_project_id},
    )
    op.alter_column("dataset", "project_id", nullable=False)
    op.alter_column("workflow", "project_id", nullable=False)

    op.add_column(
        "identifier2dataset", sa.Column("new_dataset_id", sa.Integer(), nullable=True)
    )
    op.execute(
        """
        UPDATE identifier2dataset
        SET new_dataset_id = dataset.id
        FROM dataset
        WHERE identifier2dataset.dataset = dataset.name
    """
    )
    op.drop_constraint(
        "identifier2dataset_dataset_fkey", "identifier2dataset", type_="foreignkey"
    )
    op.drop_column("identifier2dataset", "dataset")
    op.alter_column("identifier2dataset", "new_dataset_id", new_column_name="dataset")

    op.drop_constraint("dataset_pkey", "dataset", type_="primary")
    op.create_primary_key("dataset_pkey", "dataset", ["id"])
    op.create_foreign_key(
        "identifier2dataset_dataset_fkey",
        "identifier2dataset",
        "dataset",
        ["dataset"],
        ["id"],
        ondelete="CASCADE",
    )

    # ### end Alembic commands ###


def downgrade():
    # Reverse the operations
    op.drop_constraint("uq_dataset_project_id_name", "dataset", type_="unique")
    op.alter_column("dataset", "project_id", nullable=True)
    op.drop_column("dataset", "project_id")

    op.drop_constraint("uq_dataset_name", "dataset", type_="unique")
    op.drop_constraint(
        None, "dataset", type_="primary"
    )  # assumes anonymous primary key constraint
    op.drop_column("dataset", "id")

    op.execute("DROP SEQUENCE IF EXISTS dataset_id_seq;")
