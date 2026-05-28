import json
import os
import time
from typing import Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from kaapana_client.logger import get_logger
from kaapana_client.settings import get_keycloak_settings, get_services_settings

logger = get_logger(__name__)

services = get_services_settings()

KAAPANA_PROJECT_ID = os.environ["KAAPANA_PROJECT_ID"]

_TOKEN_URL = f"{services.traefik_url}/auth/realms/kaapana/protocol/openid-connect/token"
_DEVICE_CODE_URL = (
    f"{services.traefik_url}/auth/realms/kaapana/protocol/openid-connect/auth/device"
)
_DEVICE_POLL_INTERVAL = 5
_DEVICE_MAX_RETRIES = 10
# Refresh slightly before the actual expiry to avoid races.
_EXPIRY_BUFFER_SECONDS = 10


class KaapanaApiService:
    def __init__(
        self,
        root_url: str,
        project_id: str,
        client_id: str,
        client_secret: Optional[str],
    ):
        self.token = None
        self.project_cookie = None
        self._token_expiry: float | None = None
        self._get_device_code()

        self.root_url = root_url
        self.project_id = project_id
        self.client_id = client_id
        self.client_secret = client_secret

    # ------------------------------------------------------------------
    # Public HTTP methods
    # ------------------------------------------------------------------

    def get(self, endpoint=str, **kwargs):
        kwargs["url"] = f"{self.root_url}/{endpoint}"
        return requests.get(**self._with_auth(kwargs))

    def post(self, endpoint, **kwargs):
        kwargs["url"] = f"{self.root_url}/{endpoint}"
        return requests.post(**self._with_auth(kwargs))

    def put(self, endpoint, **kwargs):
        kwargs["url"] = f"{self.root_url}/{endpoint}"
        return requests.put(**self._with_auth(kwargs))

    def delete(self, endpoint, **kwargs):
        kwargs["url"] = f"{self.root_url}/{endpoint}"
        return requests.delete(**self._with_auth(kwargs))

    def head(self, endpoint, **kwargs):
        kwargs["url"] = f"{self.root_url}/{endpoint}"
        return requests.head(**self._with_auth(kwargs))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_project_cookie(self):
        r = requests.get(f"{self.root_url}/aii/projects/{KAAPANA_PROJECT_ID}")
        project_response = r.json()
        self.project_cookie = {
            "Project": json.dumps(
                {"name": project_response.get("name"), "id": KAAPANA_PROJECT_ID}
            )
        }
        return self.project_cookie

    def _with_auth(self, kwargs: dict) -> dict:
        self._ensure_valid_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.token['access_token']}"
        headers["x-forwarded-access-token"] = f"{self.token['access_token']}"
        kwargs["headers"] = headers
        verify = kwargs.pop("verify", False)
        kwargs["verify"] = verify
        cookies = kwargs.pop("cookies", {})
        project_cookie = self.project_cookie or self._get_project_cookie()
        cookies.update(project_cookie)
        kwargs["cookies"] = cookies
        return kwargs

    def _ensure_valid_token(self):
        if self.token is None:
            self._authenticate_with_device_code()
        elif self._is_token_expired():
            self._refresh_access_token()

    def _is_token_expired(self) -> bool:
        return self._token_expiry is None or time.time() >= self._token_expiry

    def _store_token(self, token_response: dict):
        self.token = token_response
        expires_in = token_response.get("expires_in", 0)
        self._token_expiry = time.time() + expires_in - _EXPIRY_BUFFER_SECONDS

    def _get_device_code(self):
        payload = {
            "client_id": self.client_id,
            "scope": "openid offline_access",
        }
        if self.client_secret:
            payload["client_secret"] = self.client_secret

        r = requests.post(_DEVICE_CODE_URL, verify=False, data=payload)
        r.raise_for_status()
        data = r.json()
        self.verification_uri_complete = data.get("verification_uri_complete")
        self.device_code = data.get("device_code")
        logger.info(
            "Open the following URL in a browser to grant the ApiService access to "
            f"Kaapana: {self.verification_uri_complete}"
        )

    def _authenticate_with_device_code(self):
        """Poll for an access token after the user has approved the device code."""
        payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": self.device_code,
            "client_id": self.client_id,
            "scope": "openid offline_access",
        }
        if self.client_secret:
            payload["client_secret"] = self.client_secret

        for attempt in range(1, _DEVICE_MAX_RETRIES + 1):
            try:
                r = requests.post(_TOKEN_URL, verify=False, data=payload)
                r.raise_for_status()
                self._store_token(r.json())
                return
            except requests.exceptions.HTTPError:
                logger.warning(
                    f"Authentication pending (attempt {attempt}/{_DEVICE_MAX_RETRIES}). "
                    f"Please open {self.verification_uri_complete} in a browser to "
                    "approve access, then wait."
                )
            time.sleep(_DEVICE_POLL_INTERVAL)

        raise RuntimeError(
            f"Device code authentication failed after {_DEVICE_MAX_RETRIES} attempts. "
            f"Open {self.verification_uri_complete} in a browser and try again."
        )

    def _refresh_access_token(self):
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.token["refresh_token"],
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        r = requests.post(_TOKEN_URL, verify=False, data=payload)
        r.raise_for_status()
        self._store_token(r.json())


def get_api_service():
    keycloak_settings = get_keycloak_settings()

    return KaapanaApiService()
