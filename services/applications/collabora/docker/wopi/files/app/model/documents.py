import base64
import binascii
import datetime
import io
import logging
import re
from dataclasses import dataclass
from typing import Iterable, Optional

from fastapi import HTTPException
from minio import Minio

log = logging.getLogger("uvicorn.error")


@dataclass
class MinioDocument:
    bucket: str
    path: str
    extension: str
    modification_time: datetime.datetime
    size: int
    version: Optional[str] = None


def encode_file_id(bucket: str, path: str) -> str:
    """
    Return the url-safe base64 encoded bucket and path as the id
    """
    return base64.urlsafe_b64encode(f"{bucket}/{path}".encode("utf-8")).decode("ascii").rstrip("=")


def decode_file_id(file_id: str) -> tuple[str, str]:
    try:
        raw = base64.urlsafe_b64decode(file_id + "=" * (-len(file_id) % 4)).decode("utf-8")
    except (binascii.Error, ValueError):
        raise HTTPException(404)
    bucket, separator, path = raw.partition("/")
    if not bucket or not separator or not path:
        raise HTTPException(404)
    return bucket, path


def extension_of(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def find_documents(
    minio: Minio, bucket: str, extensions: Iterable[str], ignore_regex: Optional[str] = None
) -> list[MinioDocument]:
    """
    Find all documents in a MinIO bucket with matching extension and not matching ignore_regex.
    """
    extensions = set(extensions)
    ignore_re = re.compile(ignore_regex) if ignore_regex else None
    docs = []
    for obj in minio.list_objects(bucket, recursive=True):
        if obj.is_dir:
            continue
        extension = extension_of(obj.object_name)
        if extension not in extensions or (ignore_re and ignore_re.match(obj.object_name)):
            continue
        docs.append(
            MinioDocument(
                bucket=bucket,
                path=obj.object_name,
                extension=extension,
                modification_time=obj.last_modified,
                size=obj.size,
                version=obj.etag,
            )
        )
    log.info("Found %i documents in %s", len(docs), bucket)
    return docs


def stat_document(minio: Minio, bucket: str, path: str) -> MinioDocument:
    obj = minio.stat_object(bucket, path)
    return MinioDocument(
        bucket=bucket,
        path=path,
        extension=extension_of(path),
        modification_time=obj.last_modified,
        size=obj.size,
        version=obj.etag,
    )


def read_document(minio: Minio, bucket: str, path: str) -> bytes:
    response = minio.get_object(bucket, path)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def write_document(minio: Minio, bucket: str, path: str, body: bytes) -> MinioDocument:
    minio.put_object(bucket, path, data=io.BytesIO(body), length=len(body))
    return stat_document(minio, bucket, path)
