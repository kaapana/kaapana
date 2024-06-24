from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from . import schemas
from . import crud

from ..database import get_session

router = APIRouter()


@router.post("", response_model=schemas.Project, tags=["Projects"])  # POST /projects
async def projects(
    project: schemas.CreateProject, session: AsyncSession = Depends(get_session)
):
    return await crud.create_project(session, project)


@router.get("/rights", response_model=List[schemas.Right], tags=["Projects"])
async def get_rights(session: AsyncSession = Depends(get_session), name: str = None):
    return await crud.get_rights(session, name=name)


@router.get("/roles", response_model=List[schemas.Role], tags=["Projects"])
async def get_roles(session: AsyncSession = Depends(get_session), name: str = None):
    return await crud.get_roles(session, name=name)


@router.post("/{project_name}/data", response_model=schemas.Data, tags=["Projects"])
async def create_data(
    project_name: str,
    data: schemas.CreateData,
    session: AsyncSession = Depends(get_session),
):
    stored_data = await crud.create_data(session, data)

    projects = await crud.get_projects(session, name=project_name)

    await crud.create_data_projects_mapping(session, project_id=projects[0].id, data_id=stored_data.id)

    return stored_data
