"""
Behavioral test for the kaapana-backend admin logout token fetch.

Guards that _get_keycloak_service_token uses client_credentials grant against
the kaapana realm — not a password grant against master.
No live Keycloak: requests.post is mocked.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

FILES_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FILES_DIR))

# Stub heavy dependencies not installed in the test environment
for mod in (
    "app.config",
    "app.dependencies",
    "app.workflows.utils",
    "fastapi",
    "fastapi.responses",
    "jwt",
    "minio",
    "minio.error",
    "starlette",
    "starlette.responses",
    "opensearchpy",
):
    sys.modules.setdefault(mod, MagicMock())

# Provide a settings stub with the attributes used by the module
settings_stub = MagicMock()
settings_stub.keycloak_url = "https://keycloak.test"
settings_stub.keycloak_service_client_secret = "test-secret"
sys.modules["app.config"].settings = settings_stub

import app.admin.routers as routers  # noqa: E402


def _fake_post(access_token: str = "fake-token"):
    resp = MagicMock()
    resp.json.return_value = {"access_token": access_token}
    resp.raise_for_status.return_value = None
    return MagicMock(return_value=resp)


def test_get_keycloak_service_token_uses_client_credentials_against_kaapana_realm():
    mock_post = _fake_post()
    with patch.object(routers.requests, "post", mock_post):
        token = routers._get_keycloak_service_token("s3cr3t")

    assert token == "fake-token"
    _, kwargs = mock_post.call_args
    url = mock_post.call_args[0][0]
    data = kwargs["data"]

    assert data["grant_type"] == "client_credentials"
    assert data["client_id"] == "kaapana-service"
    assert data["client_secret"] == "s3cr3t"
    assert "username" not in data and "password" not in data
    assert "/realms/kaapana/protocol/openid-connect/token" in url
    assert "master" not in url
