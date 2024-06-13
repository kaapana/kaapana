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
