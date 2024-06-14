from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import (
    Projects,
    Data,
    Rights,
    UsersProjectsRoles,
    DataProjects,
    RolesRights,
)


async def get_user_projects(session: AsyncSession, keycloak_id: str):
    result = await session.execute(
        select(Projects)
        .join(UsersProjectsRoles, Projects.id == UsersProjectsRoles.project_id)
        .filter(UsersProjectsRoles.keycloak_id == keycloak_id)
    )
    return result.scalars().all()


async def get_project_data(session: AsyncSession, project_id: int):
    result = await session.execute(
        select(Data)
        .join(DataProjects, Data.id == DataProjects.data_id)
        .filter(DataProjects.project_id == project_id)
    )
    return result.scalars().all()


async def get_user_rights(session: AsyncSession, keycloak_id: int):
    result = await session.execute(
        select(Rights)
        .join(RolesRights, Rights.id == RolesRights.right_id)
        .join(UsersProjectsRoles, RolesRights.role_id == UsersProjectsRoles.role_id)
        .filter(UsersProjectsRoles.keycloak_id == keycloak_id)
    )
    return result.scalars().all()
