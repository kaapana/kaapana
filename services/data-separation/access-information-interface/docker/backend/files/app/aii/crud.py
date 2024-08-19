from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import (
    Projects,
    Data,
    Rights,
    Roles,
    UsersProjectsRoles,
    DataProjects,
    RolesRights,
)


async def get_user_projects(session: AsyncSession, keycloak_id: str):
    result = await session.execute(
        select(
            Projects.id,
            Projects.name,
            Projects.description,
            Roles.id.label("role_id"),
            Roles.name.label("role_name"),
        )
        .join(UsersProjectsRoles, Projects.id == UsersProjectsRoles.project_id)
        .join(Roles, UsersProjectsRoles.role_id == Roles.id)
        .filter(UsersProjectsRoles.keycloak_id == keycloak_id)
    )
    return result.all()


async def get_user_rights(session: AsyncSession, keycloak_id: str):
    result = await session.execute(
        select(
            Rights.name,
            Rights.description,
            Rights.claim_key,
            Rights.claim_value,
            UsersProjectsRoles.project_id,
        )
        .join(RolesRights, Rights.id == RolesRights.right_id)
        .join(UsersProjectsRoles, RolesRights.role_id == UsersProjectsRoles.role_id)
        .filter(UsersProjectsRoles.keycloak_id == keycloak_id)
    )

    return result.all()


async def get_project_data(session: AsyncSession, project_id: int):
    result = await session.execute(
        select(Data)
        .join(DataProjects, Data.id == DataProjects.data_id)
        .filter(DataProjects.project_id == project_id)
    )
    return result.scalars().all()


async def get_projects(session: AsyncSession, name: str = None):
    stmt = select(Projects)
    stmt = stmt.filter(Projects.name == name) if name else stmt
    result = await session.execute(stmt)
    return result.scalars().all()
