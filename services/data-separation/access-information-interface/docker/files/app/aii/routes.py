from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..schemas import Data, AiiRightResponse, AiiProjectResponse
from .crud import get_user_projects, get_project_data, get_user_rights, get_projects

from ..database import get_session

router = APIRouter()


# @router.get("/projects/{keycloak_id}", response_model=List[Project], tags=["Aii"])
# async def projects(keycloak_id: str, session: AsyncSession = Depends(get_session)):
#    return await get_user_projects(session, keycloak_id)


@router.get("/projects/{project_name}/data", response_model=List[Data], tags=["Aii"])
async def project_data(project_name: str, session: AsyncSession = Depends(get_session)):
    projects = await get_projects(session, name=project_name)
    return await get_project_data(session, projects[0].id)


@router.get(
    "/users/{keycloak_id}/rights", response_model=List[AiiRightResponse], tags=["Aii"]
)
async def user_rights(keycloak_id: str, session: AsyncSession = Depends(get_session)):
    return await get_user_rights(session, keycloak_id)


@router.get(
    "/users/{keycloak_id}/projects",
    response_model=List[AiiProjectResponse],
    tags=["Aii"],
)
async def user_projects(keycloak_id: str, session: AsyncSession = Depends(get_session)):
    return await get_user_projects(session, keycloak_id)
