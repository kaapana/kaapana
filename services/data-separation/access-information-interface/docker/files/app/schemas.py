from pydantic import BaseModel, ConfigDict

class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class User(OrmBaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int 
    keycloak_id: 

class Projects(OrmBaseModel):
    id: int
    name: 
    description:

class Roles(OrmBaseModel):
    id:
    description:
    name:

class Rights(OrmBaseModel):
    id: int
    description:
    claim_key:
    claim_value:

class Data(OrmBaseModel):
    id: int
    description:
    data_type:

class DICOMSeries(OrmBaseModel):
    id: int
    series_instance_uid: