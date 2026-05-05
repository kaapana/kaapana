from pydantic import BaseModel
from uuid import UUID


class InstalledExtension(BaseModel):
    id: UUID
    repository_id: UUID
    tag: str
    manifest: dict
    status: str
