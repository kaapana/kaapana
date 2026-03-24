from typing import Optional
from uuid import UUID

from app.models import (
    AdminProject,
    Projects,
    Rights,
    Roles,
    RolesRights,
    SoftwareMappings,
    UsersProjectsRoles,
)
from app.projects import schemas
from sqlalchemy import delete, select, update, func, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import TEXT


def build_kubernetes_namespace(short_id: str) -> str:
    return f"project-{short_id}"


def build_s3_bucket(short_id: str) -> str:
    return f"project-{short_id}"


def build_opensearch_index(short_id: str) -> str:
    return f"project_{short_id}"


async def create_project(
    session: AsyncSession, project: schemas.CreateProject
) -> Projects:

    new_project = Projects(
        name=project.name,
        description=project.description,
        external_id=project.external_id,
    )
    session.add(new_project)
    await session.commit()
    await session.refresh(new_project)
    return new_project


async def get_admin_project(session: AsyncSession):
    result = await session.execute(
        select(Projects).join(AdminProject, Projects.id == AdminProject.project_id)
    )
    return result.scalars().first()


async def set_admin_project(session: AsyncSession, project_id: UUID):
    default_project = AdminProject(project_id=project_id)
    session.add(default_project)
    await session.commit()
    return default_project


async def get_projects(
    session: AsyncSession,
    project_id: Optional[UUID] = None,
    project_name: Optional[str] = None,
    project_short_id: Optional[str] = None,
) -> list[schemas.Project]:
    stmt = select(Projects)
    if project_id is not None:
        stmt = stmt.where(Projects.id == project_id)
    if project_short_id is not None:
        # check if first 8 chars of project id matches the provided short id
        stmt = stmt.where(func.left(cast(Projects.id, TEXT), 8) == project_short_id)
    if project_name is not None:
        stmt = stmt.where(Projects.name == project_name)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [schemas.Project.model_validate(row) for row in rows]


async def create_rights(session: AsyncSession, right: schemas.CreateRight):
    new_right = Rights(
        name=right.name,
        description=right.description,
        claim_key=right.claim_key,
        claim_value=right.claim_value,
    )
    session.add(new_right)
    await session.commit()
    return new_right


async def get_rights(session: AsyncSession, name: Optional[str] = None):
    stmt = select(Rights)
    if name:
        stmt = stmt.where(Rights.name == name)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_rights_by_role_id(session: AsyncSession, role_id: int):
    # Query Rights based on the role_id through the RolesRights table
    stmt = select(Rights).join(RolesRights).filter(RolesRights.role_id == role_id)
    # Execute the query asynchronously
    result = await session.execute(stmt)
    # Fetch all the results
    rights = result.scalars().all()

    return rights


async def create_roles(session: AsyncSession, role: schemas.CreateRole):
    new_role = Roles(name=role.name, description=role.description)
    session.add(new_role)
    await session.commit()
    return new_role


async def get_roles(session: AsyncSession, name: Optional[str] = None):
    stmt = select(Roles)
    if name:
        stmt = stmt.where(Roles.name == name)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_role(session: AsyncSession, role_id: int):
    stmt = select(Roles).where(Roles.id == role_id)
    result = await session.execute(stmt)
    return result.scalars().first()


async def create_roles_rights_mapping(
    session: AsyncSession, role_id: int, right_id: int
):
    new_role_rights = RolesRights(role_id=role_id, right_id=right_id)
    session.add(new_role_rights)
    await session.commit()
    return True


async def get_users_projects_roles_mapping(
    session: AsyncSession, project_id: UUID, keycloak_id: str
):
    # Create the select UserProjectRoles statement
    stmt = select(UsersProjectsRoles).where(
        UsersProjectsRoles.project_id == project_id,
        UsersProjectsRoles.keycloak_id == keycloak_id,
    )
    # Execute the select statement asynchronously
    result = await session.execute(stmt)

    return result.scalars().first()


async def create_users_projects_roles_mapping(
    session: AsyncSession, project_id: UUID, role_id: int, keycloak_id
):
    new_user_project_role = UsersProjectsRoles(
        project_id=project_id, role_id=role_id, keycloak_id=keycloak_id
    )
    session.add(new_user_project_role)
    await session.commit()
    return True


async def update_users_projects_roles_mapping(
    session: AsyncSession,
    project_id: UUID,
    keycloak_id: str,
    role_id: int,
):
    """
    Updates the role of a user in a specific project by mapping a new role.

    This function updates the `role_id` for the user with the given `keycloak_id`
    in the `UsersProjectsRoles` table for the specified `project_id`.
    """
    # Create the Update statement
    stmt = (
        update(UsersProjectsRoles)
        .where(
            UsersProjectsRoles.project_id == project_id,
            UsersProjectsRoles.keycloak_id == keycloak_id,
        )
        .values(role_id=role_id)
    )
    # Execute the update statement asynchronously
    await session.execute(stmt)
    # Commit the transaction to apply the deletion
    await session.commit()
    return True


async def delete_users_projects_roles_mapping(
    session: AsyncSession, project_id: UUID, keycloak_id: str
):
    # Create the delete statement
    stmt = delete(UsersProjectsRoles).where(
        UsersProjectsRoles.project_id == project_id,
        UsersProjectsRoles.keycloak_id == keycloak_id,
    )
    # Execute the delete statement asynchronously
    await session.execute(stmt)
    # Commit the transaction to apply the deletion
    await session.commit()
    return True


async def get_project_users_roles_mapping(
    session: AsyncSession,
    project_id: UUID,
):
    stmt = select(UsersProjectsRoles)
    stmt = stmt.filter(UsersProjectsRoles.project_id == project_id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_user_role_in_project(
    session: AsyncSession,
    keycloak_id: str,
    project_id: UUID,
):
    stmt = select(UsersProjectsRoles).where(
        UsersProjectsRoles.project_id == project_id,
        UsersProjectsRoles.keycloak_id == keycloak_id,
    )
    result = await session.execute(stmt)
    role_map = result.scalars().first()
    return await get_role(session, role_map.role_id)


async def get_user_rights_in_project(
    session: AsyncSession,
    keycloak_id: str,
    project_id: UUID,
):

    stmt = select(UsersProjectsRoles).where(
        (UsersProjectsRoles.project_id == project_id),
        (UsersProjectsRoles.keycloak_id == keycloak_id),
    )
    result = await session.execute(stmt)
    role_map = result.scalars().first()
    return await get_rights_by_role_id(session, role_map.role_id)


async def get_software_mappings_by_project_id(session: AsyncSession, project_id: UUID):
    stmt = select(SoftwareMappings).where(SoftwareMappings.project_id == project_id)
    result = await session.execute(stmt)
    software_mappings = result.scalars().all()
    return software_mappings


async def create_software_mapping(
    session: AsyncSession, project_id: UUID, software_uuid: str
):
    new_software_mapping = SoftwareMappings(
        software_uuid=software_uuid, project_id=project_id
    )
    session.add(new_software_mapping)
    await session.commit()
    return new_software_mapping


async def delete_software_mapping(
    session: AsyncSession, project_id: UUID, software_uuid: str
):
    stmt = delete(SoftwareMappings).where(
        SoftwareMappings.project_id == project_id,
        SoftwareMappings.software_uuid == software_uuid,
    )
    await session.execute(stmt)
    await session.commit()
    return True


async def update_project(
    session: AsyncSession, project_id: UUID, project_update: schemas.UpdateProject
):
    stmt = (
        update(Projects)
        .where(Projects.id == project_id)
        .values(**project_update.model_dump(exclude_none=True))
    )
    await session.execute(stmt)
    await session.commit()

    result = await session.execute(select(Projects).where(Projects.id == project_id))
    return result.scalars().first()


async def delete_project(session: AsyncSession, project_id: UUID):
    # Delete dependent rows first to avoid FK violations
    await session.execute(
        delete(UsersProjectsRoles).where(UsersProjectsRoles.project_id == project_id)
    )
    await session.execute(
        delete(SoftwareMappings).where(SoftwareMappings.project_id == project_id)
    )
    await session.execute(delete(Projects).where(Projects.id == project_id))
    await session.commit()
    return True
