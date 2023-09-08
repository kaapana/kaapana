from typing import Optional, List, Any
from pydantic import BaseModel, validator, root_validator


class MyBaseModel(BaseModel):
    class Config:
        orm_mode = True


class KaapanaUser(MyBaseModel):
    id: str
    name: str
    attributes: dict
    firstName: str
    lastName: str
    email: str


class KaapanaGroup(MyBaseModel):
    id: str
    name: str


class KaapanaRole(MyBaseModel):
    id: str
    name: str
    description: str = ""


class ProjectRole(KaapanaRole):
    project_role_name: str


class ProjectUser(KaapanaUser):
    projectRole: ProjectRole


class KaapanaProject(MyBaseModel):
    name: str
    group_id: str
    project_roles: list
    accesstable_primary_key: str


class AccessListEntree(MyBaseModel):
    id: int
    user: str = ""
    permissions: str = ""
    accesstable_primary_key: str = ""


class AccessTable(MyBaseModel):
    object_primary_key: str = ""
