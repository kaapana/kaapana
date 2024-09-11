from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Projects, Rights, Roles, RolesRights, UsersProjectsRoles
from . import schemas


async def create_project(session: AsyncSession, project: schemas.CreateProject):
    new_project = Projects(
        name=project.name,
        description=project.description,
        external_id=project.external_id,
    )
    session.add(new_project)
    await session.commit()
    return new_project


async def get_projects(session: AsyncSession, name: str = None):
    stmt = select(Projects)
    stmt = stmt.filter(Projects.name == name) if name else stmt
    result = await session.execute(stmt)
    return result.scalars().all()


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


async def get_rights(session: AsyncSession, name: str = None):
    stmt = select(Rights)
    stmt = stmt.filter(Rights.name == name) if name else stmt
    result = await session.execute(stmt)
    return result.scalars().all()


async def create_roles(session: AsyncSession, role: schemas.CreateRole):
    new_role = Roles(name=role.name, description=role.description)
    session.add(new_role)
    await session.commit()
    return new_role


async def get_roles(session: AsyncSession, name: str = None):
    stmt = select(Roles)
    stmt = stmt.filter(Roles.name == name) if name else stmt
    result = await session.execute(stmt)
    return result.scalars().all()


async def create_roles_rights_mapping(
    session: AsyncSession, role_id: int, right_id: int
):
    new_role_rights = RolesRights(role_id=role_id, right_id=right_id)
    session.add(new_role_rights)
    await session.commit()
    return True


async def create_users_projects_roles_mapping(
    session: AsyncSession, project_id: int, role_id: int, keycloak_id
):
    new_user_project_role = UsersProjectsRoles(
        project_id=project_id, role_id=role_id, keycloak_id=keycloak_id
    )
    session.add(new_user_project_role)
    await session.commit()
    return True