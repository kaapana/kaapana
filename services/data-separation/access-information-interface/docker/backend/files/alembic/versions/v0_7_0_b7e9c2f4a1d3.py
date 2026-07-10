"""v0-7-0 rights rename/split/remove

Revision ID: b7e9c2f4a1d3
Revises: 9f0f1d2b3c4a
Create Date: 2026-07-02 10:00:00.000000

Renames the 0.6.1 rights in place so existing roles_rights and
users_projects_roles rows keep pointing at the correct rows, and removes the
dropped right. The new split rights (view_applications, launch_application,
delete_active_apps, view_active_apps, manage_applications_whitelist) and their
default role mappings are added afterwards by the regular ConfigMap seeder
(init_scripts.initial_database_population), which runs on every startup.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e9c2f4a1d3"
down_revision: Union[str, None] = "9f0f1d2b3c4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (old_name, new_name, new_claim_key, new_claim_value, new_description)
RENAMES = [
    (
        "manage_project_users",
        "manage_users",
        "kaapana.ai/aii",
        "manage_users",
        "User can manage user roles in this project",
    ),
    (
        "open_project_applications",
        "open_applications",
        "kaapana.ai/applications",
        "open",
        "User can open running applications in the selected project.",
    ),
    (
        "manage_project_extensions",
        "manage_workflow_whitelist",
        "kaapana.ai/workflows",
        "manage",
        "User can edit the project workflow whitelist",
    ),
]

REMOVED = "manage_project_software"


def upgrade() -> None:
    """Upgrade schema."""
    for old_name, new_name, claim_key, claim_value, description in RENAMES:
        op.execute(
            f"""
            UPDATE rights
            SET name = '{new_name}',
                claim_key = '{claim_key}',
                claim_value = '{claim_value}',
                description = '{description}'
            WHERE name = '{old_name}'
            """
        )

    op.execute(
        f"""
        DELETE FROM roles_rights
        WHERE right_id IN (SELECT id FROM rights WHERE name = '{REMOVED}')
        """
    )
    op.execute(f"DELETE FROM rights WHERE name = '{REMOVED}'")


def downgrade() -> None:
    """Downgrade schema."""
    # Revert renames (old claim_key/value/description from 0.6.1)
    op.execute(
        """
        UPDATE rights
        SET name = 'manage_project_users',
            claim_key = 'kaapana.ai/aii',
            claim_value = 'manage_users',
            description = 'User can manage user roles in this project'
        WHERE name = 'manage_users'
        """
    )
    op.execute(
        """
        UPDATE rights
        SET name = 'open_project_applications',
            claim_key = 'kaapana.ai/applications',
            claim_value = 'open',
            description = 'User can access multiinstallable applications in the selected project.'
        WHERE name = 'open_applications'
        """
    )
    op.execute(
        """
        UPDATE rights
        SET name = 'manage_project_extensions',
            claim_key = 'kaapana.ai/extensions',
            claim_value = 'manage',
            description = 'User can install projects in the extensions view'
        WHERE name = 'manage_workflow_whitelist'
        """
    )
    # Re-create the removed right
    op.execute(
        """
        INSERT INTO rights (name, description, claim_key, claim_value)
        SELECT 'manage_project_software',
               'User can manage software availabel to this project',
               'kaapana.ai/aii',
               'manage_software'
        WHERE NOT EXISTS (SELECT 1 FROM rights WHERE name = 'manage_project_software')
        """
    )
