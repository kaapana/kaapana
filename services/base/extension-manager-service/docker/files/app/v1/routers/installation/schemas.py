from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from v1.services.database.models import ExtensionOrigin
from v1.services.oci.models import ExtensionManifest


class InstalledContent(BaseModel):
    name: str
    content_type: str
    status: str
    location: Optional[str]


class InstalledExtension(BaseModel):
    id: UUID
    repository_id: Optional[UUID]
    tag: str
    origin: ExtensionOrigin
    uploaded_by: Optional[str]
    uploaded_filename: Optional[str]
    reason: Optional[str]
    manifest: ExtensionManifest
    status: str
    contents: list[InstalledContent]
