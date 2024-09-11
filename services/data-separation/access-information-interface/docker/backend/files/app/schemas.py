from pydantic import BaseModel, ConfigDict


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
