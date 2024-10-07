import logging
from typing import List

from app.keycloak_helper import KeycloakHelper
from app.schemas import KeycloakUser
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.get("", response_model=List[KeycloakUser], tags=["Users"])
async def get_users():
    kc_client = KeycloakHelper()

    keycloak_users_json = kc_client.get_users()
    users = []

    for kc_user in keycloak_users_json:
        user = KeycloakUser(**kc_user)
        users.append(user)

    return users


@router.get("/{keycloak_id}", response_model=KeycloakUser, tags=["Users"])
async def get_keycloak_user_by_id(
    keycloak_id: str,
):
    kc_client = KeycloakHelper()

    keycloak_user_json = kc_client.get_user_by_id(keycloak_id)
    if not keycloak_user_json:
        raise HTTPException(status_code=404, detail="User not found")

    user = KeycloakUser(**keycloak_user_json)
    return user


@router.get("/username/{username}", response_model=KeycloakUser, tags=["Users"])
async def get_keycloak_user_by_name(
    username: str,
):
    kc_client = KeycloakHelper()

    keycloak_user_json = kc_client.get_user_by_name(username)
    if not keycloak_user_json:
        raise HTTPException(status_code=404, detail="User not found")

    user = KeycloakUser(**keycloak_user_json)

    return user
