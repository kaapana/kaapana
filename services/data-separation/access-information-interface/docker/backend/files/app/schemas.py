from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# AII


class AiiRightResponse(OrmBaseModel):
    name: str
    description: str
    claim_key: str
    claim_value: str
    project_id: int


class AiiProjectResponse(OrmBaseModel):
    id: int
    name: str
    description: str
    role_id: int
    role_name: str


class KeycloakUser(BaseModel):
    id: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email_verified: bool


class KeycloakUserExtended(KeycloakUser):
    groups: Optional[list[str]] = None
    realm_roles: Optional[list[str]] = None
