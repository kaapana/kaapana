import uuid
from typing import Optional

from pydantic import BaseModel, Field, SecretStr
from v1.services.oci.models import ExtensionManifest


### Request schemas
class PostRepositoryRequest(BaseModel):
    name: str = Field(..., description="The human-readable name of the registry entry.")
    description: str = Field(
        default="",
        description="An optional description for the registry entry.",
    )

    repository_url: str = Field(
        ...,
        description="The full URL of the repository to be added. <registry>/<repository>",
    )

    username: str = Field(..., description="Name of the access token to the registry")
    password: SecretStr = Field(..., description="The access token to the registry")


class PutRepositoryRequest(BaseModel):
    name: Optional[str] = Field(
        None, description="The human-readable name of the registry entry."
    )
    description: Optional[str] = Field(
        default=None,
        description="An optional description for the registry entry.",
    )

    repository_url: Optional[str] = Field(
        None,
        description="The full URL of the repository to be added. <registry>/<repository>",
    )
    username: str = Field(..., description="Name of the access token to the registry")
    password: SecretStr = Field(..., description="The access token to the registry")


### Response schemas


class Repository(BaseModel):
    name: str = Field(..., description="The human-readable name of the registry entry.")
    description: str = Field(
        default="",
        description="An optional description for the registry entry.",
    )

    repository_url: str = Field(
        ...,
        description="The full URL of the repository to be added. <registry>/<repository>",
    )

    id: uuid.UUID = Field(
        ..., description="The unique identifier of the registry entry."
    )


############ Extensions ###############


class ExtensionsManifestsResponse(BaseModel):
    repository_id: uuid.UUID = Field(
        ...,
        description="The unique identifier of the repository this extension belongs to.",
    )
    tag: str = Field(..., description="The tag of the extension.")
    manifest: ExtensionManifest
