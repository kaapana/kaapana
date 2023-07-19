from typing import Optional, List, Any
from pydantic import BaseModel, validator, root_validator


class MyBaseModel(BaseModel):
    class Config:
        orm_mode = True


class KaapanaUser(MyBaseModel):
    idx: str
    name: str
    attributes: dict
    firstName: str
    lastName: str
    email: str


class KaapanaGroup(MyBaseModel):
    idx: str
    name: str


class KaapanaRole(MyBaseModel):
    idx: str
    name: str
    description: str = ""


class KaapanaProject(MyBaseModel):
    name: str
    role_admin_idx: str
    role_member_idx: str
    group_idx: str
