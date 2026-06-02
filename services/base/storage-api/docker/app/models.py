from __future__ import annotations

from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class PacsCoordinate(BaseModel):
    type: Literal["pacs"] = "pacs"
    pacs_id: str = Field(..., description="DICOMweb endpoint base URL of the PACS")
    study_uid: str
    series_uid: Optional[str] = None
    instance_uid: Optional[str] = None


class S3Coordinate(BaseModel):
    type: Literal["s3"] = "s3"
    bucket: str
    key: str
    region: Optional[str] = None
    endpoint_url: Optional[str] = None
    is_prefix: bool = Field(
        False,
        description="If true, `key` is a folder prefix and all objects under it are "
        "fetched (relative structure preserved); else `key` is a single object.",
    )


class FilesystemCoordinate(BaseModel):
    type: Literal["filesystem"] = "filesystem"
    volume: str
    path: str


class UrlCoordinate(BaseModel):
    type: Literal["url"] = "url"
    url: str
    hint: Optional[str] = None


Coordinate = Annotated[
    Union[PacsCoordinate, S3Coordinate, FilesystemCoordinate, UrlCoordinate],
    Field(discriminator="type"),
]


class DownloadItem(BaseModel):
    """A group of coordinates archived under a shared opaque prefix.

    Callers (e.g. the workflow download task) pass the data-entity id as `id`;
    the storage-api treats it as an opaque archive prefix and never resolves it.
    """

    id: str = Field(..., description="Opaque archive prefix for this item's files")
    coordinates: List[Coordinate]


class DownloadRequest(BaseModel):
    items: List[DownloadItem]
    format: Literal["tar", "zip"] = "tar"


class S3UploadTarget(BaseModel):
    """Write arbitrary files (models, archives, …) as objects under a prefix."""

    store: Literal["s3"] = "s3"
    bucket: str = Field(..., description="Target MinIO/S3 bucket")
    key_prefix: str = Field(
        "", description="Object-key prefix; file paths are appended to it"
    )
    unit: Literal["file", "folder"] = Field(
        "folder",
        description="'folder': store all files under the prefix and return one "
        "prefix coordinate; 'file': store the single uploaded file and return one "
        "object coordinate.",
    )


class PacsUploadTarget(BaseModel):
    """Write DICOM instances back to a PACS via DICOMweb STOW-RS."""

    store: Literal["pacs"] = "pacs"
    pacs_id: Optional[str] = Field(
        None,
        description="DICOMweb endpoint base URL; defaults to the in-cluster store",
    )


UploadTarget = Annotated[
    Union[S3UploadTarget, PacsUploadTarget], Field(discriminator="store")
]


class UploadResponse(BaseModel):
    """The storage coordinates the written bytes are now addressable by.

    The caller (e.g. the workflow upload task) records these on a new Data API
    entity — the storage-api itself never touches the Data API.
    """

    coordinates: List[Coordinate]
