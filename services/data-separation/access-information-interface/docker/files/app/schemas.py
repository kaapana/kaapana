from pydantic import BaseModel, ConfigDict


class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class User(OrmBaseModel):
    keycloak_id: str


class Project(OrmBaseModel):
    id: int
    name: str
    description: str


class Right(OrmBaseModel):
    description: str
    claim_key: str
    claim_value: str


class Role(OrmBaseModel):
    description: str
    name: str


class Data(OrmBaseModel):
    description: str
    data_type: str
    series_instance_uid: str


class DICOMSeries(Data):
    series_instance_uid: str


class DummyDataType(Data):
    dummy_text: str


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
