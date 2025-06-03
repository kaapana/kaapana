import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from threading import Lock

import requests
from kaapanapy.settings import KaapanaSettings
from minio import Minio

from . import get_project_user_access_token


class HelperMinioSessionManager:
    """
    Helper class to manage Minio client sessions with automatic token refresh.
    This class ensures that the Minio client is always valid by checking the expiration of the access token
    and refreshing it when necessary.
    It uses a lock to ensure thread safety when accessing the client.
    """

    def __init__(self):
        self._client = None
        self._expiration = None
        self._lock = Lock()

    def get_client(self):
        with self._lock:
            if self._is_expired():
                self._refresh_client()
            return self._client

    def _minio_credentials_with_expiration(self):
        # make sure to get a fresh access token, because the old one might be expired.
        access_token = get_project_user_access_token()
        r = requests.post(
            f"http://minio-service.{KaapanaSettings().services_namespace}.svc:9000"
            f"?Action=AssumeRoleWithWebIdentity&WebIdentityToken={access_token}&Version=2011-06-15"
        )
        r.raise_for_status()
        xml_response = r.text
        root = ET.fromstring(xml_response)
        ns = {"ns": "https://sts.amazonaws.com/doc/2011-06-15/"}
        credentials = root.find(".//ns:Credentials", ns)
        access_key_id = credentials.find("ns:AccessKeyId", ns).text
        secret_access_key = credentials.find("ns:SecretAccessKey", ns).text
        session_token = credentials.find("ns:SessionToken", ns).text
        expiration = credentials.find(
            "ns:Expiration", ns
        ).text  # e.g. "2025-06-02T12:55:00Z"
        return access_key_id, secret_access_key, session_token, expiration

    def _is_expired(self):
        if not self._expiration:
            return True
        return datetime.now(timezone.utc) > self._expiration - timedelta(minutes=2)

    def _refresh_client(self):
        access_key, secret_key, session_token, expiration_str = (
            self._minio_credentials_with_expiration()
        )
        self._expiration = datetime.fromisoformat(expiration_str.replace("Z", "+00:00"))

        self._client = Minio(
            f"minio-service.{KaapanaSettings().services_namespace}.svc:9000",
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            secure=False,
        )
