from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator
import re


class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreateProject(OrmBaseModel):
    external_id: Optional[str] = None
    name: str
    description: str

    @field_validator("name", mode="before")
    @classmethod
    def validate_project_name(cls, v):
        """
        Validate if the project name satisfies naming rules for buckets in minio, namespaces in kubernetes and indices in opensearch.
        """
        assert type(v) == str
        ### minio-naming-rules
        if len(v) > 63 - len("project-"):
            raise AssertionError("Project names must be at max 55 charackters")
        if v.endswith("-s3alias"):
            raise AssertionError(
                "Project names must not end with the suffix -s3alias. This suffix is reserved for access point alias names."
            )
        if v.startswith("."):
            raise AssertionError("Project names must not start with a dot!")
        if ".." in v or ".-" in v or "-." in v:
            raise AssertionError(
                "Project names must not contain two adjacent periods (dots), or a period adjacent to a hyphen"
            )
        if not re.match(r"^[a-z0-9.-]*$", v):
            raise AssertionError(
                "Project names can consist only of lowercase letters, numbers, dots (.), and hyphens (-)."
            )
        ### kubernetes namespace naming rules
        if not re.match(r"^[a-z0-9.-]*$", v):
            raise AssertionError(
                "Project names can consist only consist of lower case alphanumeric characters, -, and ."
            )
        ### opensearch
        ### Would be redundant to the upper naming rules

        return v


class Project(OrmBaseModel):
    id: int
    external_id: Optional[str] = None
    name: str
    description: str
    kubernetes_namespace: str
    s3_bucket: str
    opensearch_index: str


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
