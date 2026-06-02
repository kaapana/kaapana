from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Iterator, Optional, Tuple

from app.config import get_settings
from app.models import S3Coordinate

from .base import StorageBackend

logger = logging.getLogger(__name__)

_STS_NS = {"ns": "https://sts.amazonaws.com/doc/2011-06-15/"}
_TIMEOUT = 30


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

        # Single object → one file at the entity-folder root.
        data = self._get_object(client, coordinate.bucket, coordinate.key)
        name = coordinate.key.rstrip("/").split("/")[-1] or "object"
        yield name, data
