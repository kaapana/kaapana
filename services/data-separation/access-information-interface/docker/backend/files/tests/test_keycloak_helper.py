"""
Unit tests for the AII KeycloakHelper auth changeover (#1918).

Guards that the helper authenticates via the kaapana-service client using a
client_credentials grant against the kaapana realm — not the old admin
username/password grant against master. No live Keycloak: requests.post is
mocked.
"""

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Make the app package importable and stub kaapanapy (not installed in test env).
FILES_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FILES_DIR))
sys.modules.setdefault("kaapanapy", MagicMock())
sys.modules.setdefault("kaapanapy.logger", MagicMock())

import app.keycloak_helper as kh  # noqa: E402


def _fake_post():
    """A requests.post replacement that returns a token without erroring."""
    resp = MagicMock()
    resp.json.return_value = {"access_token": "fake-token"}
    resp.raise_for_status.return_value = None
    post = MagicMock(return_value=resp)
    return post


def test_get_access_token_uses_client_credentials_against_kaapana_realm():
    post = _fake_post()
    with patch.object(kh.requests, "post", post):
        kh.KeycloakHelper(
            client_secret="s3cr3t",
            keycloak_host="keycloak-internal-service.admin.svc",
            keycloak_https_port=443,
        )

    assert post.call_count == 1
    args, kwargs = post.call_args
    url = args[0] if args else kwargs["url"]
    data = kwargs["data"]

    assert data["grant_type"] == "client_credentials"
    assert data["client_id"] == "kaapana-service"
    assert data["client_secret"] == "s3cr3t"
    assert "username" not in data and "password" not in data
    assert "/realms/kaapana/protocol/openid-connect/token" in url
    assert "master" not in url


def test_init_reads_service_client_secret_from_env_without_admin_creds(monkeypatch):
    # The old admin env vars must no longer be required.
    monkeypatch.delenv("KEYCLOAK_USER", raising=False)
    monkeypatch.delenv("KEYCLOAK_PASSWORD", raising=False)
    monkeypatch.setenv("KEYCLOAK_SERVICE_CLIENT_SECRET", "env-secret")
    monkeypatch.setenv("KEYCLOAK_HOST", "keycloak-internal-service.admin.svc")

    post = _fake_post()
    with patch.object(kh.requests, "post", post):
        helper = kh.KeycloakHelper()  # no args -> must come from env

    assert helper.client_secret == "env-secret"
    # token request used the env secret via client_credentials
    _, kwargs = post.call_args
    assert kwargs["data"]["client_secret"] == "env-secret"
    assert kwargs["data"]["grant_type"] == "client_credentials"
