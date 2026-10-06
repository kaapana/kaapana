from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from v1.services.oci.models import ExtensionManifest


class InstalledContent(BaseModel):
    name: str
    content_type: str
    status: str
    location: Optional[str] = None


class InstalledExtension(BaseModel):
    id: UUID
    repository_id: Optional[UUID] = None
    repository_name: Optional[str] = None
    repository_url: Optional[str] = None
    tag: str
    manifest: ExtensionManifest
    status: str
    contents: list[InstalledContent]
