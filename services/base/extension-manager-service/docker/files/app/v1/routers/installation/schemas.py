from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from v1.services.oci.models import ExtensionManifest


class InstalledContent(BaseModel):
    name: str
    content_type: str
    status: str
    location: str


class InstalledExtension(BaseModel):
    id: UUID
    repository_id: UUID
    tag: str
    manifest: ExtensionManifest
    status: str
    contents: list[InstalledContent]
