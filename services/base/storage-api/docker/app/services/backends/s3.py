from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from io import BytesIO
from typing import Iterable, Iterator, List, Optional, Tuple

from app.config import get_settings
from app.models import S3Coordinate

from .base import StorageBackend, StorageError

logger = logging.getLogger(__name__)

_STS_NS = {"ns": "https://sts.amazonaws.com/doc/2011-06-15/"}
_TIMEOUT = 30


@contextmanager
def _translate_s3_errors() -> Iterator[None]:
    """Map a MinIO ``S3Error`` that carries a 4xx (e.g. ``AccessDenied`` -> 403)
    to a neutral :class:`StorageError`, so the API returns that status instead
    of a 500. Anything else (5xx, no status) propagates unchanged — a genuine
    upstream failure should still surface as a 500.
    """
    from minio.error import S3Error

    try:
        yield
    except S3Error as exc:
        status = getattr(exc.response, "status", None)
        if isinstance(status, int) and 400 <= status < 500:
            raise StorageError(
                status, exc.message or exc.code or "Object store request rejected"
            ) from exc
        raise


def _safe_relpath(filename: str) -> str:
    """Normalise an upload file path to a safe relative key segment.

    Preserves sub-directory structure (so an uploaded folder keeps its layout)
    but strips traversal: drops leading slashes, ``.``/``..`` segments and any
    Windows drive/backslash, so a crafted name can't escape the prefix.
    """
    normalised = filename.replace("\\", "/")
    parts = [p for p in normalised.split("/") if p not in ("", ".", "..")]
    return "/".join(parts) or "object"


def _minio_client(access_token: str, endpoint: str):
    """Exchange the caller's access token for temporary MinIO credentials.

    Mirrors ``kaapanapy.helper.HelperMinioSessionManager`` (AssumeRoleWith-
    WebIdentity) so storage-api needs no static MinIO secret and inherits the
    caller's project scope.
    """
    import requests
    from minio import Minio

    response = requests.post(
        f"http://{endpoint}?Action=AssumeRoleWithWebIdentity"
        f"&WebIdentityToken={access_token}&Version=2011-06-15",
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    creds = ET.fromstring(response.text).find(".//ns:Credentials", _STS_NS)
    if creds is None:
        raise ValueError("MinIO STS response did not contain credentials")

    def _field(tag: str) -> str:
        element = creds.find(f"ns:{tag}", _STS_NS)
        if element is None or element.text is None:
            raise ValueError(f"MinIO STS response missing credential field '{tag}'")
        return element.text

    return Minio(
        endpoint,
        access_key=_field("AccessKeyId"),
        secret_key=_field("SecretAccessKey"),
        session_token=_field("SessionToken"),
        secure=False,
    )


class S3Backend(StorageBackend):
    store_type = "s3"

    def _get_object(self, client, bucket: str, key: str) -> bytes:
        with _translate_s3_errors():
            response = client.get_object(bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def fetch(
        self, coordinate: S3Coordinate, access_token: Optional[str]
    ) -> Iterator[Tuple[str, bytes]]:
        if not access_token:
            raise ValueError(
                "S3 download requires an access token for web-identity auth"
            )

        endpoint = get_settings().minio_url
        client = _minio_client(access_token, endpoint)

        if not coordinate.is_prefix:
            # Single object → one file at the entity-folder root.
            data = self._get_object(client, coordinate.bucket, coordinate.key)
            name = coordinate.key.rstrip("/").split("/")[-1] or "object"
            yield name, data
            return

        # Folder coordinate → every object under the prefix, internal structure
        # preserved (relpath is the object key minus the prefix).
        prefix = coordinate.key
        if prefix and not prefix.endswith("/"):
            prefix += "/"
        with _translate_s3_errors():
            for obj in client.list_objects(
                coordinate.bucket, prefix=prefix, recursive=True
            ):
                key = obj.object_name
                if key.endswith("/"):  # skip explicit directory markers
                    continue
                relpath = key[len(prefix) :] or key.rsplit("/", 1)[-1]
                yield relpath, self._get_object(client, coordinate.bucket, key)

    def store(
        self,
        target,
        files: Iterable[Tuple[str, bytes]],
        access_token: Optional[str],
    ) -> List[S3Coordinate]:
        if not access_token:
            raise ValueError("S3 upload requires an access token for web-identity auth")

        endpoint = get_settings().minio_url
        client = _minio_client(access_token, endpoint)

        prefix = target.key_prefix or ""
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        unit = getattr(target, "unit", "folder")
        files = list(files)
        if unit == "file":
            if len(files) != 1:
                raise ValueError(
                    f"Upload unit 'file' expects exactly one file, got {len(files)}"
                )
        elif not prefix:
            # A folder coordinate with an empty prefix would later list the whole
            # bucket on fetch — refuse it rather than mint that footgun.
            raise ValueError("Upload unit 'folder' requires a non-empty key_prefix")

        coordinates: List[S3Coordinate] = []
        for filename, content in files:
            # Preserve the relative path under the prefix (so an uploaded folder keeps
            # its structure), but defend the object namespace against traversal.
            relpath = _safe_relpath(filename)
            key = f"{prefix}{relpath}"
            with _translate_s3_errors():
                client.put_object(
                    target.bucket,
                    key,
                    BytesIO(content),
                    length=len(content),
                )
            if unit == "file":
                # Single object coordinate addressing exactly this key.
                coordinates.append(S3Coordinate(bucket=target.bucket, key=key))

        if unit == "folder":
            # One coordinate for the whole folder; fetch lists everything under it.
            coordinates.append(
                S3Coordinate(bucket=target.bucket, key=prefix, is_prefix=True)
            )
        return coordinates
