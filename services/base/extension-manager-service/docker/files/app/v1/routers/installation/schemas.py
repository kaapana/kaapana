from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from v1.services.oci.models import ExtensionManifest


class InstalledContent(BaseModel):
    name: str
    content_type: str
    status: str
    location: Optional[str] = None
    applied_version: Optional[str] = None


class PendingUpdate(BaseModel):
    repository_id: UUID
    tag: str
    manifest: ExtensionManifest


class InstalledExtension(BaseModel):
    id: UUID
    repository_id: UUID
    tag: str
    manifest: ExtensionManifest
    pending_update: Optional[PendingUpdate] = None
    status: str
    contents: list[InstalledContent]
