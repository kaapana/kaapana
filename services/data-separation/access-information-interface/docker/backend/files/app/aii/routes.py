from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..schemas import AiiProjectResponse, AiiRightResponse
from .crud import get_user_projects, get_user_rights

router = APIRouter()


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
