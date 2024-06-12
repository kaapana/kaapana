from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import schemas
import crud
from database import get_session

router = APIRouter()


@router.get("/projects", response_model=List[schemas.Projects])
async def projects(keycloak_id: str, session: AsyncSession = Depends(get_session)):
    return await crud.get_user_projects(session, keycloak_id)


@router.get("/projects/{project_id}/data/{data_type}", response_model=List[schemas.Data])
async def project_data(project_id: int, session: AsyncSession = Depends(get_session)):
    return await crud.get_project_data(session, project_id)


@router.get("/users/{user_id}/rights", response_model=List[schemas.Rights])
async def user_rights(user_id: int, session: AsyncSession = Depends(get_session)):
    return await crud.get_user_rights(session, user_id)
