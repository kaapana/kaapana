from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sqlalchemy import select
from ..models import Projects, Rights, Roles, RolesRights
from . import schemas


async def create_project(session: AsyncSession, project: schemas.CreateProject):
    new_project = Projects(name=project.name, description=project.description)
    session.add(new_project)
    await session.commit()
    return new_project

async def create_rights(session: AsyncSession, right: schemas.CreateRight):
    new_right = Rights(name=right.name, description=right.description, claim_key=right.claim_key, claim_value=right.claim_value)
    session.add(new_right)
    await session.commit()
    return new_right

async def get_rights(session: AsyncSession):
    result = await session.execute(select(Rights))
    return result.scalars().all()

async def create_roles(session: AsyncSession, role: schemas.CreateRole):
    new_role = Roles(name=role.name, description=role.description)
    session.add(new_role)
    await session.commit()
    return new_role

async def get_roles(session: AsyncSession):
    result = await session.execute(select(Roles))
    return result.scalars().all()

async def create_roles_rights_mapping(session: AsyncSession, role_id: int, right_id: int):
    await session.execute(RolesRights.insert().values(role_id=role_id, right_id=right_id))
    await session.commit()
    return True