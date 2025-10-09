"""v0-5-0

Revision ID: 6e751c62ecfa
Revises: 100ab450e292
Create Date: 2025-04-02 11:36:19.761275

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "6e751c62ecfa"
down_revision: Union[str, None] = "100ab450e292"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.drop_constraint(
        "data_projects_data_id_fkey",  # Name of the FK constraint
        "data_projects",  # Table that has the FK
        type_="foreignkey",
    )

    op.drop_table(
        "data",
    )
    op.drop_table(
        "data_projects",
    )

    """Upgrade schema."""
    # Add UUID columns to tables
    op.add_column(
        "projects",
        sa.Column(
            "project_uuid", UUID(as_uuid=True), nullable=True, default=uuid.uuid4
        ),
    )
    op.add_column(
        "users_projects_roles",
        sa.Column("project_uuid", UUID(as_uuid=True), nullable=True),
    )

    # Update UUID column with new UUID values
    # Use Python's `uuid.uuid4()` for generating UUIDs for each row
    op.execute(
        """
        UPDATE projects SET project_uuid = gen_random_uuid();
        """
    )
    # Update foreign key columns in related tables to point to the new UUID
    op.execute(
        """
        UPDATE users_projects_roles
        SET project_uuid = (SELECT project_uuid FROM projects WHERE projects.id = users_projects_roles.project_id)
    """
    )

    op.alter_column("projects", "project_uuid", nullable=False)
    op.alter_column("users_projects_roles", "project_uuid", nullable=False)

    op.drop_constraint(
        "users_projects_roles_project_id_fkey",
        "users_projects_roles",
        type_="foreignkey",
    )

    # Remove the foreign and primary key constraints
    # op.drop_column("software_mappings", "project_id")
    # op.drop_column("users_projects_roles", "project_id")
    op.drop_constraint("projects_pkey", "projects", type_="primary")

    # Rename old id to int_id
    op.alter_column(
        "projects",
        "id",
        new_column_name="int_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # Rename new uuid_id to uuid
    op.alter_column(
        "projects",
        "project_uuid",
        new_column_name="id",
        existing_type=UUID(as_uuid=True),
    )

    # Add a new primary key constraint on the UUID `id` column in `projects`
    op.create_primary_key("projects_pkey", "projects", ["id"])

    op.drop_column("users_projects_roles", "project_id")
    op.alter_column(
        "users_projects_roles",
        "project_uuid",
        new_column_name="project_id",
        nullable=False,
    )

    # Create new foreign keys on the `project_id` columns, now pointing to the new `id` column in `projects`
    op.create_foreign_key(
        "users_projects_roles_project_id_fkey",
        "users_projects_roles",
        "projects",
        ["project_id"],
        ["id"],  # Referencing the UUID `id` column in `projects`
    )

    op.create_table(
        "admin_project",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("project_id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.execute(
        """
        INSERT INTO admin_project (project_id)
        SELECT id FROM projects WHERE int_id = 1
    """
    )
    op.create_table(
        "software_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("software_uuid", sa.String(length=72), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "software_uuid"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Add back the integer foreign key columns in dependent tables
    op.drop_table("admin_project")

    op.add_column(
        "software_mappings",
        sa.Column("project_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "users_projects_roles",
        sa.Column("project_id", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE software_mappings
        SET project_id = (SELECT int_id FROM projects WHERE projects.id = software_mappings.project_id)
        """
    )
    op.execute(
        """
        UPDATE users_projects_roles
        SET project_id = (SELECT int_id FROM projects WHERE projects.id = users_projects_roles.project_id)
        """
    )

    # Drop the old foreign key constraints
    op.drop_constraint(
        "software_mappings_project_id_fkey", "software_mappings", type_="foreignkey"
    )
    op.drop_constraint(
        "users_projects_roles_project_id_fkey",
        "users_projects_roles",
        type_="foreignkey",
    )

    # Drop the UUID foreign key columns
    op.drop_column("software_mappings", "project_id")
    op.drop_column("users_projects_roles", "project_id")
    op.drop_column("projects", "id")

    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                next_val INTEGER;
            BEGIN
                LOOP
                    SELECT nextval('projects_int_id_seq') INTO next_val;
                    UPDATE projects
                    SET int_id = next_val
                    WHERE int_id IS NULL
                    RETURNING int_id;
                    EXIT WHEN NOT FOUND;
                END LOOP;
            END
            $$;
            """
        )
    )

    # Rename `temp_id` back to `id` in `projects`
    op.alter_column(
        "projects",
        "int_id",
        new_column_name="id",
        existing_type=sa.Integer(),
    )

    # Recreate the primary key on `id` (integer)
    op.create_primary_key("projects_pkey", "projects", ["id"])

    # Recreate foreign keys to reference the new integer `id`
    op.create_foreign_key(
        "software_mappings_project_id_fkey",
        "software_mappings",
        "projects",
        ["project_id"],
        ["id"],
    )
    op.create_foreign_key(
        "users_projects_roles_project_id_fkey",
        "users_projects_roles",
        "projects",
        ["project_id"],
        ["id"],
    )
    op.drop_table("software_mappings")
    # ### end Alembic commands ###
