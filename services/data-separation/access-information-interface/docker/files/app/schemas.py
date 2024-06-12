from pydantic import BaseModel, ConfigDict


class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Users(OrmBaseModel):
    id: int
    keycloak_id: str


class Projects(OrmBaseModel):
    id: int
    name: str
    description: str


class Roles(OrmBaseModel):
    description: str
    name: str


class Rights(OrmBaseModel):
    description: str
    claim_key: str
    claim_value: str


class Data(OrmBaseModel):
    description: str
    data_type: str


class DICOMSeries(Data):
    series_instance_uid: str


class DummyDataType(Data):
    dummy_text: str
