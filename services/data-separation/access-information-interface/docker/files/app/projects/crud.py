from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Projects
from . import schemas


async def create_project(session: AsyncSession, project: schemas.CreateProject):
    new_project = Projects(name=project.name, description=project.description)
    session.add(new_project)
    await session.commit()
    return new_project
