from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from .schemas import Project, CreateProject, Right
from . import crud

from ..database import get_session

router = APIRouter()


@router.post("", response_model=Project, tags=["Projects"])  # POST /projects
async def projects(
    project: CreateProject, session: AsyncSession = Depends(get_session)
):
    return await crud.create_project(session, project)

@router.get("/rights", response_model=List[Right], tags=["Projects"])
async def get_rights(session: AsyncSession = Depends(get_session)):
    return await crud.get_rights(session)