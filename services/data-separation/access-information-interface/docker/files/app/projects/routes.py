from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from .schemas import Project, CreateProject
from .crud import create_project

from ..database import get_session

router = APIRouter()


@router.post("", response_model=Project, tags=["Projects"])  # POST /projects
async def projects(
    project: CreateProject, session: AsyncSession = Depends(get_session)
):
    return await create_project(session, project)
