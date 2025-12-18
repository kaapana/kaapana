from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# AII


class AiiRightResponse(OrmBaseModel):
    name: str
    description: str
    claim_key: str
    claim_value: str
    project_id: UUID


class AiiProjectResponse(OrmBaseModel):
    id: UUID
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

    @computed_field
    @property
    def system(self) -> bool:
        return self.last_name is not None and self.last_name.lower() == "system"


class KeycloakUserExtended(KeycloakUser):
    groups: Optional[list[str]] = None
    realm_roles: Optional[list[str]] = None
