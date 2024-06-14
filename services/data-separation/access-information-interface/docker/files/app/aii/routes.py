from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..schemas import Project, Data, Right
from .crud import get_user_projects, get_project_data, get_user_rights

from ..database import get_session

router = APIRouter()


@router.get("/projects", response_model=List[Project], tags=["Aii"])
async def projects(keycloak_id: str, session: AsyncSession = Depends(get_session)):
    return await get_user_projects(session, keycloak_id)


@router.get("/projects/{project_id}/data", response_model=List[Data], tags=["Aii"])
async def project_data(project_id: int, session: AsyncSession = Depends(get_session)):
    return await get_project_data(session, project_id)


@router.get("/users/{user_id}/rights", response_model=List[Right], tags=["Aii"])
async def user_rights(user_id: int, session: AsyncSession = Depends(get_session)):
    return await get_user_rights(session, user_id)
