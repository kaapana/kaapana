from pydantic import BaseModel, ConfigDict


class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class User(OrmBaseModel):
    keycloak_id: str


class Project(OrmBaseModel):
    id: int
    name: str
    description: str


class Role(OrmBaseModel):
    description: str
    name: str


class Right(OrmBaseModel):
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
