import logging
from typing import List

from app.database import get_session
from app.keycloak_helper import KeycloakHelper, get_keycloak_helper
from app.schemas import AiiProjectResponse, KeycloakUser
from app.users import crud
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.get("", response_model=List[KeycloakUser], tags=["Users"])
async def get_users(kc_client: KeycloakHelper = Depends(get_keycloak_helper)):
    """Get all the Users from Keycloak"""

    keycloak_users_json = kc_client.get_users()
    users = []

    for kc_user in keycloak_users_json:
        user = KeycloakUser(**kc_user)
        users.append(user)

    return users


@router.get("/username/{username}", response_model=KeycloakUser, tags=["Users"])
async def get_keycloak_user_by_name(
    username: str, kc_client: KeycloakHelper = Depends(get_keycloak_helper)
):
    """Get the specific user by username"""

    keycloak_user_json = kc_client.get_user_by_name(username)
    if not keycloak_user_json:
        raise HTTPException(status_code=404, detail="User not found")

    user = KeycloakUser(**keycloak_user_json)

    return user


@router.get("/{keycloak_id}", response_model=KeycloakUser, tags=["Users"])
async def get_keycloak_user_by_id(
    keycloak_id: str, kc_client: KeycloakHelper = Depends(get_keycloak_helper)
):
    """Get specific user by keycloak id"""

    keycloak_user_json = kc_client.get_user_by_id(keycloak_id)
    if not keycloak_user_json:
        raise HTTPException(status_code=404, detail="User not found")

    user = KeycloakUser(**keycloak_user_json)
    return user


@router.get(
    "/{keycloak_id}/projects", response_model=List[AiiProjectResponse], tags=["Users"]
)
async def get_all_projects_by_user_id(
    keycloak_id: str,
    session: AsyncSession = Depends(get_session),
    kc_client: KeycloakHelper = Depends(get_keycloak_helper),
):
    """Get projects the user is in"""

    user = await get_keycloak_user_by_id(keycloak_id, kc_client)
    response_list = await crud.get_user_projects(session, user.id)
    projects = []

    # Convert SQLAlchemy output to a list of AiiProjectResponse schema
    # sql alchemy output is JOIN output from users_projects_roles, projects, roles table
    for users_projects_roles, project, role in response_list:
        # Map SQLAlchemy models to Pydantic schema
        response = AiiProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            role_id=role.id,
            role_name=role.name,
        )
        projects.append(response)

    return projects
