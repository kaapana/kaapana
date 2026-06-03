from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class StoreType(str, Enum):
    PACS = "pacs"
    S3 = "s3"
    FILESYSTEM = "filesystem"
    URL = "url"


class BaseStorageCoordinate(BaseModel):
    """Base description of where a data entity is stored and how to retrieve it."""

    type: StoreType = Field(
        ..., description="Type of the store (e.g. pacs, s3, filesystem, url)"
    )


class PacsStorageCoordinate(BaseStorageCoordinate):
    type: StoreType = StoreType.PACS
    pacs_id: str = Field(..., description="Identifier of the PACS system")
    study_uid: str = Field(..., description="DICOM Study Instance UID")
    series_uid: Optional[str] = Field(None, description="DICOM Series Instance UID")
    instance_uid: Optional[str] = Field(None, description="DICOM SOP Instance UID")


class S3StorageCoordinate(BaseStorageCoordinate):
    type: StoreType = StoreType.S3
    bucket: str
    key: str
    region: Optional[str] = None
    endpoint_url: Optional[HttpUrl] = None
    is_prefix: bool = Field(
        False,
        description="If true, `key` is a folder prefix addressing all objects under "
        "it; if false, `key` is a single object",
    )


class FilesystemStorageCoordinate(BaseStorageCoordinate):
    type: StoreType = StoreType.FILESYSTEM
    volume: str = Field(..., description="Volume or mount name")
    path: str = Field(..., description="File path on the volume")


class UrlStorageCoordinate(BaseStorageCoordinate):
    type: StoreType = StoreType.URL
    url: HttpUrl
    hint: Optional[str] = Field(
        None, description="Optional hint on how to use this URL"
    )


StorageCoordinate = (
    PacsStorageCoordinate
    | S3StorageCoordinate
    | FilesystemStorageCoordinate
    | UrlStorageCoordinate
)


class Artifact(BaseModel):
    """Binary or auxiliary file uploaded to the service (e.g. thumbnails).

    The actual bytes are stored by the service (e.g. on local
    disk or object storage) and are addressed by the `id`.
    """

    id: str = Field(
        ..., description="Stable identifier of the artifact within a metadata entry"
    )
    filename: Optional[str] = Field(None, description="Original or suggested filename")
    content_type: Optional[str] = Field(
        None, description="MIME type of the artifact content"
    )
    size_bytes: Optional[int] = Field(
        None, ge=0, description="Size of the artifact in bytes, if known"
    )


class MetadataEntry(BaseModel):
    """Schema-validated metadata attached to a data entity under a specific key."""

    key: str = Field(
        ..., description="Metadata key (must have a registered JSON Schema)"
    )
    data: Dict[str, Any] = Field(
        ..., description="Metadata payload validated against the key's JSON Schema"
    )
    artifacts: List[Artifact] = Field(
        default_factory=list,
        description="Artifacts associated with this metadata entry",
    )


class EntityLink(BaseModel):
    """Directed, typed edge between two data entities, with optional properties."""

    id: UUID = Field(..., description="Stable UUID identifying this link")
    source_id: UUID = Field(
        ..., description="UUID of the entity the link originates from"
    )
    target_id: UUID = Field(..., description="UUID of the entity the link points to")
    link_type: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Free-form edge type; the string 'contains' is treated as a tree edge",
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary JSON properties attached to this edge",
    )
    created_at: Optional[datetime] = Field(
        None, description="Timestamp when the link was created (UTC)"
    )


class EntityLinkCreate(BaseModel):
    """Request body for creating a new outgoing link from a source entity."""

    target_id: UUID = Field(..., description="UUID of the target entity")
    link_type: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Edge type; 'contains' is cycle-checked server-side",
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Optional JSON properties for the edge"
    )


class DataEntity(BaseModel):
    """Top-level logical data entity identified by a UUID."""

    id: UUID = Field(..., description="Stable UUID that identifies this data entity")
    created_at: Optional[datetime] = Field(
        None,
        description="Timestamp when the entity was first created (UTC)",
    )
    storage_coordinates: List[StorageCoordinate] = Field(
        default_factory=list,
        description="One or many storage coordinates where the entity's bytes can be retrieved",
    )
    metadata: List[MetadataEntry] = Field(
        default_factory=list,
        description="Metadata entries attached to this data entity",
    )
    outgoing_links: List[EntityLink] = Field(
        default_factory=list,
        description="Edges originating from this entity (read-only; mutated via the links endpoint)",
    )
    incoming_links: List[EntityLink] = Field(
        default_factory=list,
        description="Edges pointing at this entity (read-only; mutated via the links endpoint)",
    )
