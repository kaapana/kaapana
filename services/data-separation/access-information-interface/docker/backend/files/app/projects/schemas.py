from pydantic import BaseModel, ConfigDict
from typing import Optional


class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreateProject(OrmBaseModel):
    external_id: Optional[str] = None
    name: str
    description: str


class Project(OrmBaseModel):
    id: int
    external_id: Optional[str] = None
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


class CreateData(OrmBaseModel):
    description: str
    data_type: str
    series_instance_uid: str


class Data(OrmBaseModel):
    id: int
    description: str
    data_type: str
    series_instance_uid: str
