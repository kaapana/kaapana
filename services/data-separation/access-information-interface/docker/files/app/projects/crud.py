from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import Projects, Rights
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