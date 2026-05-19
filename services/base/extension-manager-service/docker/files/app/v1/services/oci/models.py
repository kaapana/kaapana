from pydantic import BaseModel
import uuid


class ContentFiles(BaseModel):
    path: str


class Content(BaseModel):
    name: str
    contentType: str
    files: list[ContentFiles]


class ExtensionManifest(BaseModel):
    id: uuid.UUID
    name: str
    version: str
    contents: list[Content]
    dependencies: list
