"""
Unit tests for the AII KeycloakHelper.

Guards that the helper authenticates via the kaapana-service client
(client_credentials grant) against the kaapana realm, and that deleting a user
that is already gone is no error.
No live Keycloak: requests.post and requests.delete are mocked.
"""

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

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


def _helper():
    with patch.object(kh.requests, "post", _fake_post()):
        return kh.KeycloakHelper(
            client_secret="s3cr3t", keycloak_host="keycloak", keycloak_https_port=443
        )


def _answer(status):
    response = requests.Response()
    response.status_code = status
    return response


def test_delete_user_sends_delete_to_the_user_url():
    helper = _helper()
    with patch.object(kh.requests, "delete", return_value=_answer(204)) as delete:
        helper.delete_user("abc")
    delete.assert_called_once()
    assert (
        delete.call_args.args[0]
        == "https://keycloak:443/auth/admin/realms/kaapana/users/abc"
    )
    assert delete.call_args.kwargs["headers"]["Authorization"] == "Bearer fake-token"


def test_delete_user_accepts_a_user_that_is_already_gone():
    helper = _helper()
    with patch.object(kh.requests, "delete", return_value=_answer(404)):
        helper.delete_user("abc")


def test_delete_user_raises_other_errors():
    helper = _helper()
    with patch.object(kh.requests, "delete", return_value=_answer(500)):
        with pytest.raises(requests.HTTPError):
            helper.delete_user("abc")
