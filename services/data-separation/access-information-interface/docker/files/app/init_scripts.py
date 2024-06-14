from .projects.crud import (
    create_rights,
    create_roles,
    create_roles_rights_mapping,
    get_roles,
    get_rights,
    create_project,
    create_users_projects_roles_mapping,
    get_projects,
)
from .projects.schemas import CreateRight, CreateRole, CreateProject
from .database import async_session
from sqlalchemy.exc import IntegrityError
import logging
import json
from keycloak import KeycloakAdmin
import os

logger = logging.getLogger(__name__)


def load_config(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


async def initial_database_population():
    config_path = "/app/config"
    config_files = {
        "initial_rights": os.path.join(config_path, "initial_rights.json"),
        "initial_roles": os.path.join(config_path, "initial_roles.json"),
        "initial_roles_rights_mapping": os.path.join(
            config_path, "initial_roles_rights_mapping.json"
        ),
        "initial_projects": os.path.join(config_path, "initial_projects.json"),
    }

    config_data = {
        key: load_config(path) for key, path in config_files.items()
    }  # Load the config files

    async with async_session() as session:
        # Init rights
        init_rights = [
            CreateRight(**right) for right in config_data["initial_rights"]
        ]  # Could crash if the config file is not compatible with the schema
        for right in init_rights:
            try:
                await create_rights(session, right)
            except IntegrityError:
                logger.warning(f"Right {right.name} already exists")
                await session.rollback()

        # Init roles
        init_roles = [CreateRole(**role) for role in config_data["initial_roles"]]
        for role in init_roles:
            try:
                await create_roles(session, role)
            except IntegrityError:
                logger.warning(f"Role {role.name} already exists")
                await session.rollback()

        # init role mappings
        role_mappings = config_data["initial_roles_rights_mapping"]
        for role_mapping in role_mappings:
            role = await get_roles(session, name=role_mapping["role"])
            for right_name in role_mapping["rights"]:
                right = await get_rights(session, name=right_name)
                try:
                    await create_roles_rights_mapping(session, role[0].id, right[0].id)
                except IntegrityError:
                    logger.warning(
                        f"RolesRights mapping for {role_mapping['role']} and {right_name} already exists"
                    )
                    await session.rollback()
                    role = await get_roles(session, name=role_mapping["role"])

        # Init projects
        init_projects = [
            CreateProject(**project) for project in config_data["initial_projects"]
        ]
        for project in init_projects:
            try:
                await create_project(session, project)
            except IntegrityError:
                logger.warning(f"Project {project.name} already exists")
                await session.rollback()

        # Keycloak server details
        kaapana_realm = os.environ.get("KEYCLOAK_REALM")
        admin_user_in_kaapana_realm = os.environ.get("KEYCLOAK_KAAPANA_REALM_USER_NAME")

        # Initialize KeycloakAdmin
        keycloak_admin = KeycloakAdmin(
            server_url=os.environ.get("KEYCLOAK_URL"),
            username=os.environ.get("KEYCLOAK_ADMIN_USER_NAME"),
            password=os.environ.get("KEYCLOAK_ADMIN_USER_PASSWORD"),
            verify=False,  # Set to False to disable SSL verification
        )

        keycloak_admin.get_realms() # I dont know why, but without this line it throws authentication errors

        # Switch to the kaapana realm
        keycloak_admin.change_current_realm(kaapana_realm)

        # Give admin user the admin role in the admin project
        admin_user_keycloak_id = keycloak_admin.get_user_id(
            username=admin_user_in_kaapana_realm
        )

        if not admin_user_keycloak_id:
            logger.error(f"User {admin_user_in_kaapana_realm} not found in keycloak")
            return

        admin_role = await get_roles(session, name="admin")
        admin_project = await get_projects(session, name="admin")

        try:
            await create_users_projects_roles_mapping(
                session=session, keycloak_id=admin_user_keycloak_id, project_id=admin_project[0].id, role_id=admin_role[0].id
            )
        except IntegrityError:
            logger.warning(
                f"User {admin_user_in_kaapana_realm} already has the admin role in the admin project"
            )
            await session.rollback()
