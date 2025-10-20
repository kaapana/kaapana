import json
import os
import xml.etree.ElementTree as ET

import time
import requests
from requests.adapters import HTTPAdapter, Retry

from kaapanapy.settings import (
    KaapanaSettings,
    OpensearchSettings,
    OperatorSettings,
    KeycloakSettings,
    ProjectSettings,
)
from minio import Minio
from opensearchpy import OpenSearch


def get_opensearch_client(access_token=None) -> OpenSearch:
    settings = OpensearchSettings()
    access_token = access_token or get_project_user_access_token()
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    return OpenSearch(
        hosts=[
            {
                "host": settings.opensearch_host,
                "port": settings.opensearch_port,
            }
        ],
        http_compress=True,  # enables gzip compression for request bodies
        use_ssl=True,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        timeout=10,
        headers=auth_headers,
    )


def get_minio_client(access_token=None) -> Minio:
    """
    :access_token: Access token that should be used for communication with minio.
    """
    access_token = access_token or get_project_user_access_token()
    access_key, secret_key, session_token = minio_credentials(access_token)

    return Minio(
        f"minio-service.{KaapanaSettings().services_namespace}.svc:9000",
        access_key=access_key,
        secret_key=secret_key,
        session_token=session_token,
        secure=False,
    )


def minio_credentials(access_token):
    r = requests.post(
        f"http://minio-service.{KaapanaSettings().services_namespace}.svc:9000?Action=AssumeRoleWithWebIdentity&WebIdentityToken={access_token}&Version=2011-06-15"
    )
    xml_response = r.text
    root = ET.fromstring(xml_response)
    credentials = root.find(".//{https://sts.amazonaws.com/doc/2011-06-15/}Credentials")
    access_key_id = credentials.find(
        ".//{https://sts.amazonaws.com/doc/2011-06-15/}AccessKeyId"
    ).text
    secret_access_key = credentials.find(
        ".//{https://sts.amazonaws.com/doc/2011-06-15/}SecretAccessKey"
    ).text
    session_token = credentials.find(
        ".//{https://sts.amazonaws.com/doc/2011-06-15/}SessionToken"
    ).text
    return access_key_id, secret_access_key, session_token


def load_workflow_config():
    """
    Load and return the workflow config.
    """
    settings = OperatorSettings()
    config_path = os.path.join(settings.workflow_dir, "conf", "conf.json")
    with open(config_path, "r") as f:
        config = json.load(f)
    return config


# Global in-memory cache
_token_cache = {
    "access_token": None,
    "refresh_token": None,
    "expires_at": 0,  # unix timestamp when access token expires
}

# Configure retry session for resiliency
_session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=1,  # exponential backoff (1s, 2s, 4s…)
    status_forcelist=[429, 500, 502, 503, 504],
)
_session.mount("https://", HTTPAdapter(max_retries=retries))
_session.mount("http://", HTTPAdapter(max_retries=retries))


def _token_endpoint():
    keycloak_settings = KeycloakSettings()
    return (
        f"{keycloak_settings.keycloak_url}/auth/realms/"
        f"{keycloak_settings.client_id}/protocol/openid-connect/token"
    )


def _fetch_new_token():
    """Do a password grant to fetch a fresh token set."""
    project_settings = ProjectSettings()
    keycloak_settings = KeycloakSettings()
    payload = {
        "username": project_settings.project_user_name,
        "password": project_settings.project_user_password,
        "client_id": keycloak_settings.client_id,
        "client_secret": keycloak_settings.client_secret,
        "grant_type": "password",
    }
    resp = _session.post(_token_endpoint(), data=payload, timeout=5, verify=False)
    resp.raise_for_status()
    tokens = resp.json()

    _token_cache["access_token"] = tokens["access_token"]
    _token_cache["refresh_token"] = tokens.get("refresh_token")
    # Save expiry timestamp (with a small safety margin)
    _token_cache["expires_at"] = time.time() + tokens.get("expires_in", 60) - 30


def _refresh_token():
    """Try to refresh using the cached refresh token."""
    keycloak_settings = KeycloakSettings()
    payload = {
        "client_id": keycloak_settings.client_id,
        "client_secret": keycloak_settings.client_secret,
        "grant_type": "refresh_token",
        "refresh_token": _token_cache["refresh_token"],
    }
    resp = _session.post(_token_endpoint(), data=payload, timeout=5, verify=False)
    resp.raise_for_status()
    tokens = resp.json()

    _token_cache["access_token"] = tokens["access_token"]
    _token_cache["refresh_token"] = tokens.get("refresh_token")
    _token_cache["expires_at"] = time.time() + tokens.get("expires_in", 60) - 30


def get_project_user_access_token():
    """
    Return a cached access token of the project user.
    Will refresh or re-login as needed.
    """
    now = time.time()

    # If cached and not expired, return it
    if _token_cache["access_token"] and now < _token_cache["expires_at"]:
        return _token_cache["access_token"]

    # Try refresh if we have a refresh token
    if _token_cache["refresh_token"]:
        try:
            _refresh_token()
            return _token_cache["access_token"]
        except Exception:
            # Refresh failed, fall back to full login
            pass

    # Fallback: get a new token via password grant
    _fetch_new_token()
    return _token_cache["access_token"]
