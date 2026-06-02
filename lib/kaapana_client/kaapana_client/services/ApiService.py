import json
import os
import time
from typing import Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from kaapana_client import settings
from kaapana_client.logger import get_logger

logger = get_logger(__name__)

_DEVICE_POLL_INTERVAL = 5
_DEVICE_MAX_RETRIES = 10
# Refresh slightly before the actual expiry to avoid races.
_EXPIRY_BUFFER_SECONDS = 10


class KaapanaApiService:
    """
    Use objects of KaapanaApiService to authenticate against Kaapana and make authenticated requests to Kaapana APIs.

    Supported Oauth2 Grants:
    * Device code grant
    """

    def __init__(
        self,
        root_url: str,
        project_id: str,
        client_id: str,
        client_secret: Optional[str] = None,
        oidc_metadata_url: str = "/auth/realms/kaapana/.well-known/openid-configuration",
        verify: bool = False,
    ):
        """Initialize the service and start the OAuth2 device code flow.

        Fetches the project cookie and initiates device authorization. The user
        must visit the printed URL to grant access before the first API call is
        made.

        Args:
            root_url: Base URL of the Kaapana instance (e.g. the Traefik gateway
                URL). All endpoint paths are appended to this value.
            project_id: Kaapana project identifier used to scope requests to the
                correct project.
            client_id: OAuth2 client ID registered in Keycloak.
            client_secret: OAuth2 client secret for the given client, or ``None``
                for public clients.
        """
        self.root_url = root_url
        self.project_id = project_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.oidc_metadata_url = oidc_metadata_url
        self.verify = verify

        self.token = {}
        self._token_expiry: float | None = None
        self.project_cookie = {}
        self._fetch_oidc_metadata()
        self._get_device_code()

    # ------------------------------------------------------------------
    # Public HTTP methods
    # ------------------------------------------------------------------

    def get(self, endpoint=str, **kwargs):
        """Send an authenticated HTTP GET request.

        Args:
            endpoint: API path relative to ``root_url`` (e.g. ``"aii/datasets"``).
            **kwargs: Additional keyword arguments forwarded to ``requests.get``
                (e.g. ``params``, ``timeout``).

        Returns:
            requests.Response: The response from the server.
        """
        kwargs["url"] = f"{self.root_url}/{endpoint}"
        kwargs = self._set_project_cookie(kwargs)
        return requests.get(**self._with_auth(kwargs))

    def post(self, endpoint, **kwargs):
        """Send an authenticated HTTP POST request.

        Args:
            endpoint: API path relative to ``root_url``.
            **kwargs: Additional keyword arguments forwarded to ``requests.post``
                (e.g. ``json``, ``data``, ``timeout``).

        Returns:
            requests.Response: The response from the server.
        """
        kwargs["url"] = f"{self.root_url}/{endpoint}"
        kwargs = self._set_project_cookie(kwargs)
        return requests.post(**self._with_auth(kwargs))

    def put(self, endpoint, **kwargs):
        """Send an authenticated HTTP PUT request.

        Args:
            endpoint: API path relative to ``root_url``.
            **kwargs: Additional keyword arguments forwarded to ``requests.put``
                (e.g. ``json``, ``data``, ``timeout``).

        Returns:
            requests.Response: The response from the server.
        """
        kwargs["url"] = f"{self.root_url}/{endpoint}"
        kwargs = self._set_project_cookie(kwargs)
        return requests.put(**self._with_auth(kwargs))

    def delete(self, endpoint, **kwargs):
        """Send an authenticated HTTP DELETE request.

        Args:
            endpoint: API path relative to ``root_url``.
            **kwargs: Additional keyword arguments forwarded to ``requests.delete``
                (e.g. ``params``, ``timeout``).

        Returns:
            requests.Response: The response from the server.
        """
        kwargs["url"] = f"{self.root_url}/{endpoint}"
        kwargs = self._set_project_cookie(kwargs)
        return requests.delete(**self._with_auth(kwargs))

    def head(self, endpoint, **kwargs):
        """Send an authenticated HTTP HEAD request.

        Args:
            endpoint: API path relative to ``root_url``.
            **kwargs: Additional keyword arguments forwarded to ``requests.head``
                (e.g. ``params``, ``timeout``).

        Returns:
            requests.Response: The response from the server (no body).
        """
        kwargs["url"] = f"{self.root_url}/{endpoint}"
        kwargs = self._set_project_cookie(kwargs)
        return requests.head(**self._with_auth(kwargs))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_oidc_metadata(self):
        """Discover token and device-authorization endpoints from the OIDC metadata document.

        Fetches ``{root_url}/auth/realms/kaapana/.well-known/openid-configuration``
        and stores ``token_endpoint`` as ``self.token_url`` and
        ``device_authorization_endpoint`` as ``self.device_code_url``.

        Raises:
            requests.HTTPError: If the metadata endpoint returns a non-2xx status.
            KeyError: If the expected endpoint keys are absent from the document.
        """
        url = self.root_url + "/" + self.oidc_metadata_url
        r = requests.get(url, verify=self.verify)
        r.raise_for_status()
        metadata = r.json()
        self.token_url = metadata["token_endpoint"]
        self.device_code_url = metadata["device_authorization_endpoint"]

    def _set_project_cookie(self, kwargs: dict):
        """
        Set the project-cookie in the kwargs.
        """

        cookies = kwargs.pop("cookies", {})
        cookies.update(self.project_cookie or self._get_project_cookie())
        kwargs["cookies"] = cookies
        return kwargs

    def _get_project_cookie(self):
        """Fetch project metadata and build the ``Project`` cookie dict.

        Calls the AII projects endpoint and constructs a cookie containing the project
        name and ID in JSON form, which must accompany every API request.

        Returns:
            dict: A single-key dict ``{"Project": "<json-string>"}`` ready to
                be passed as the ``cookies`` argument to ``requests``.
        """
        r = requests.get(
            **self._with_auth(
                {
                    "url": f"{self.root_url}/aii/projects/{self.project_id}",
                    "verify": False,
                }
            )
        )

        project_response = r.json()
        self.project_cookie = {
            "Project": json.dumps(
                {"name": project_response.get("name"), "id": self.project_id}
            )
        }
        return self.project_cookie

    def _with_auth(self, kwargs: dict) -> dict:
        """Inject authentication headers and the project cookie into a kwargs dict.

        Ensures the access token is valid (refreshing it if necessary), then
        adds ``Authorization`` and ``x-forwarded-access-token`` headers and
        merges the project cookie. TLS verification defaults to ``False`` if
        not already provided by the caller.

        Args:
            kwargs: Keyword arguments intended for a ``requests`` call. Modified
                in-place and returned. Must already contain the ``url`` key.

        Returns:
            dict: The same ``kwargs`` dict with auth headers and cookies added.
        """
        self._ensure_valid_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.token['access_token']}"
        headers["x-forwarded-access-token"] = f"{self.token['access_token']}"
        kwargs["headers"] = headers
        verify = kwargs.pop("verify", False)
        kwargs["verify"] = verify
        return kwargs

    def _ensure_valid_token(self):
        """Guarantee that a non-expired access token is available.

        Triggers the full device code authentication flow if no token has been
        obtained yet, or refreshes the existing token when it has expired (or
        is within ``_EXPIRY_BUFFER_SECONDS`` of expiry).
        """
        if self.token.get("access_token") is None:
            self._authenticate_with_device_code()
        elif self._is_token_expired():
            self._refresh_access_token()

    def _is_token_expired(self) -> bool:
        """Check whether the current access token has expired (or is about to).

        Returns:
            bool: ``True`` if no expiry is recorded or if the current time is
                at or past ``_token_expiry`` (which already includes a
                ``_EXPIRY_BUFFER_SECONDS`` safety margin).
        """
        return self._token_expiry is None or time.time() >= self._token_expiry

    def _store_token(self, token_response: dict):
        """Persist a token response and compute its expiry timestamp.

        Args:
            token_response: Decoded JSON body of a successful Keycloak token
                response. Expected to contain at least ``access_token``,
                ``refresh_token``, and ``expires_in`` keys.
        """
        self.token = token_response
        expires_in = token_response.get("expires_in", 0)
        self._token_expiry = time.time() + expires_in - _EXPIRY_BUFFER_SECONDS

    def _get_device_code(self):
        """Request a device code from Keycloak and prompt the user to authenticate.

        Posts to the device authorization endpoint using ``client_id`` (and
        optionally ``client_secret``) to obtain a ``device_code`` and a
        ``verification_uri_complete``. Both are stored as instance attributes.
        The URI is logged at INFO level so the user knows where to grant access.

        Raises:
            requests.HTTPError: If the device authorization endpoint returns a
                non-2xx status code.
        """
        payload = {
            "client_id": self.client_id,
            "scope": "openid",
        }
        if self.client_secret:
            payload["client_secret"] = self.client_secret

        r = requests.post(self.device_code_url, data=payload, verify=self.verify)
        r.raise_for_status()
        data = r.json()
        self.verification_uri_complete = data.get("verification_uri_complete")
        self.device_code = data.get("device_code")
        logger.info(
            "Open the following URL in a browser to grant the ApiService access to "
            f"Kaapana: {self.verification_uri_complete}"
        )

    def _authenticate_with_device_code(self):
        """Poll Keycloak for an access token after the user has approved the device code.

        Retries up to ``_DEVICE_MAX_RETRIES`` times with ``_DEVICE_POLL_INTERVAL``
        seconds between attempts, logging a warning on each pending attempt. On
        success the token is stored via ``_store_token``.

        Raises:
            RuntimeError: If the maximum number of attempts is exhausted without
                a successful token response.
        """
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
                r = requests.post(self.token_url, verify=self.verify, data=payload)
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
        """Obtain a new access token using the stored refresh token.

        Posts a ``refresh_token`` grant to the Keycloak token endpoint and
        stores the resulting token via ``_store_token``.

        Raises:
            requests.HTTPError: If the token endpoint returns a non-2xx status
                (e.g. the refresh token has expired or been revoked).
        """
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.token["refresh_token"],
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        r = requests.post(self.token_url, verify=self.verify, data=payload)
        r.raise_for_status()
        self._store_token(r.json())


def get_api_service_from_env():
    """
    Initialize an object of KaapanaApiService based on environment variables.
    """

    keycloak_settings = settings.get_keycloak_settings()
    project_settings = settings.get_project_settings()
    service_settings = settings.get_services_settings()

    if not project_settings.project_id:
        logger.warning(
            "Project id is not set as environment variable. Could not provide KaapanaApiService"
        )
        return

    return KaapanaApiService(
        root_url=service_settings.traefik_url,
        project_id=project_settings.project_id,
        client_id=keycloak_settings.client_id,
        client_secret=keycloak_settings.client_secret,
        oidc_metadata_url=keycloak_settings.oidc_metadata_url,
    )
