from pydantic import BaseModel


class ContentFiles(BaseModel):
    path: str


class Content(BaseModel):
    name: str
    contentType: str
    files: list[ContentFiles]


class ExtensionManifest(BaseModel):
    name: str
    version: str
    contents: list[Content]
    dependencies: list
