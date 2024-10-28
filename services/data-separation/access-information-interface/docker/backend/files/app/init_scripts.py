import json
import logging
import os

from sqlalchemy.exc import IntegrityError

from .database import async_session
from .projects.crud import (
    create_rights,
    create_roles,
    create_roles_rights_mapping,
    get_rights,
    get_roles,
)
from .projects.schemas import CreateRight, CreateRole

logger = logging.getLogger(__name__)

NUM_RETRIES = 10
DURATION_BETWEEN_RETRIES = 5


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
