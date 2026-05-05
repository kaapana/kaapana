from pydantic import BaseModel, Field
import uuid
from typing import Optional


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

    authentication: str = Field(..., description="Base64 encoded credentials.")


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
    authentication: Optional[str] = Field(
        None, description="Base64 encoded authentication data."
    )


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


class ExtensionManifest(BaseModel):
    name: str = Field(..., description="The name of the extension.")
    version: str = Field(..., description="The version of the extension.")
    manifest: dict = Field(..., description="The full manifest of the extension.")
