import logging
import re
from typing import List

from app.database import get_session
from app.schemas import KeycloakUser
from app.users.KeycloakHelper import KeycloakHelper
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Utility function to convert camelCase to snake_case
def camel_to_snake(data: dict):
    def camel_to_snake_str(name):
        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    return {camel_to_snake_str(key): value for key, value in data.items()}


@router.get("", response_model=List[KeycloakUser], tags=["Users"])
async def get_users(session: AsyncSession = Depends(get_session)):
    kc_client = KeycloakHelper()

    keycloak_users_json = kc_client.get_users()
    users = []

    for kc_user in keycloak_users_json:
        snake_case_json = camel_to_snake(kc_user)
        user = KeycloakUser(**snake_case_json)
        users.append(user)

    return users


@router.get("/{keycloak_id}", response_model=KeycloakUser, tags=["Users"])
async def get_keycloak_user_by_id(
    keycloak_id: str, session: AsyncSession = Depends(get_session)
):
    kc_client = KeycloakHelper()

    keycloak_user_json = kc_client.get_user_by_id(keycloak_id)
    snake_case_json = camel_to_snake(keycloak_user_json)
    user = KeycloakUser(**snake_case_json)

    return user


@router.get("/username/{username}", response_model=KeycloakUser, tags=["Users"])
async def get_keycloak_user_by_id(
    username: str, session: AsyncSession = Depends(get_session)
):
    kc_client = KeycloakHelper()

    keycloak_user_json = kc_client.get_user_by_name(username)
    snake_case_json = camel_to_snake(keycloak_user_json)
    user = KeycloakUser(**snake_case_json)

    return user
