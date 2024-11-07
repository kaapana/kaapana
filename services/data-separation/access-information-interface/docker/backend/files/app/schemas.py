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
    first_name: str
    last_name: str
    email_verified: bool
    groups: list[str]
