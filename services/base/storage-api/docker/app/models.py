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
