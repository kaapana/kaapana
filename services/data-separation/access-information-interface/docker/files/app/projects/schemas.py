from pydantic import BaseModel, ConfigDict


class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreateProject(OrmBaseModel):
    name: str
    description: str


class Project(OrmBaseModel):
    id: int
    name: str
    description: str

class CreateRight(OrmBaseModel):
    claim_key: str
    claim_value: str
    name: str
    description: str

class Right(OrmBaseModel):
    id: int
    name: str
    description: str
    claim_key: str
    claim_value: str

class CreateRole(OrmBaseModel):
    name: str
    description: str

class Role(OrmBaseModel):
    id: int
    description: str
    name: str
