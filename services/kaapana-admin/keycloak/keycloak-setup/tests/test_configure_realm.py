"""
Behavioral tests for configure_realm.py.

Tests the helper functions and the fallback path that syncs Keycloak secrets
when admin auth is unavailable. No live Keycloak: HTTP calls are mocked.

Run from anywhere:
    pytest services/kaapana-admin/keycloak/keycloak-setup/tests/test_configure_realm.py
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# Set required env vars before module-level code in configure_realm runs
os.environ.setdefault("DEV_MODE", "false")

FILES_DIR = Path(__file__).resolve().parent.parent / "docker" / "files"
sys.path.insert(0, str(FILES_DIR))

# Stub local modules not installed in the test environment
sys.modules.setdefault("KeycloakHelper", MagicMock())
sys.modules.setdefault("logger", MagicMock())

import configure_realm as cr  # noqa: E402

# --- _service_client_functional -----------------------------------------------


def test_service_client_functional_returns_true_on_200():
    resp = MagicMock()
    resp.status_code = 200
    with patch.object(cr.requests, "post", return_value=resp) as mock_post:
        assert cr._service_client_functional("host", 443, "secret") is True

    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    url = mock_post.call_args[0][0]
    data = kwargs["data"]
    assert data["grant_type"] == "client_credentials"
    assert data["client_id"] == "kaapana-service"
    assert data["client_secret"] == "secret"
    assert "username" not in data and "password" not in data
    assert "/realms/kaapana/protocol/openid-connect/token" in url
    assert "master" not in url


def test_service_client_functional_returns_false_on_401():
    resp = MagicMock()
    resp.status_code = 401
    with patch.object(cr.requests, "post", return_value=resp):
        assert cr._service_client_functional("host", 443, "secret") is False


def test_service_client_functional_returns_false_on_exception():
    with patch.object(cr.requests, "post", side_effect=Exception("connection refused")):
        assert cr._service_client_functional("host", 443, "secret") is False


# --- _update_oidc_client_secret -----------------------------------------------


def test_update_oidc_client_secret_calls_get_then_put():
    get_resp = MagicMock()
    get_resp.json.return_value = [{"id": "client-uuid", "clientId": "kaapana"}]
    get_resp.raise_for_status.return_value = None

    put_resp = MagicMock()
    put_resp.raise_for_status.return_value = None

    with patch.object(
        cr.requests, "get", return_value=get_resp
    ) as mock_get, patch.object(cr.requests, "put", return_value=put_resp) as mock_put:
        cr._update_oidc_client_secret("host", 443, "token", "new-secret")

    get_url = mock_get.call_args[0][0]
    assert "clients?clientId=kaapana" in get_url

    put_url = mock_put.call_args[0][0]
    assert "clients/client-uuid" in put_url
    assert mock_put.call_args[1]["json"]["secret"] == "new-secret"
    assert mock_put.call_args[1]["headers"]["Authorization"] == "Bearer token"


# --- _reset_system_user_password ----------------------------------------------


def test_reset_system_user_password_calls_get_then_put():
    get_resp = MagicMock()
    get_resp.json.return_value = [{"id": "user-uuid", "username": "system"}]
    get_resp.raise_for_status.return_value = None

    put_resp = MagicMock()
    put_resp.status_code = 204
    put_resp.raise_for_status.return_value = None

    with patch.object(
        cr.requests, "get", return_value=get_resp
    ) as mock_get, patch.object(cr.requests, "put", return_value=put_resp) as mock_put:
        cr._reset_system_user_password("host", 443, "token", "new-password")

    get_url = mock_get.call_args[0][0]
    assert "users?username=system" in get_url

    put_url = mock_put.call_args[0][0]
    assert "users/user-uuid/reset-password" in put_url
    put_json = mock_put.call_args[1]["json"]
    assert put_json["value"] == "new-password"
    assert put_json["temporary"] is False


def test_reset_system_user_password_accepts_keycloak_policy_rejection():
    get_resp = MagicMock()
    get_resp.json.return_value = [{"id": "user-uuid"}]
    get_resp.raise_for_status.return_value = None

    put_resp = MagicMock()
    put_resp.status_code = 400
    put_resp.json.return_value = {"errorMessage": "Password policy not met"}

    with patch.object(cr.requests, "get", return_value=get_resp), patch.object(
        cr.requests, "put", return_value=put_resp
    ):
        cr._reset_system_user_password("host", 443, "token", "same-password")
        # Must not raise — Keycloak rejected the reset due to password policy.


def test_reset_system_user_password_raises_on_unexpected_400():
    get_resp = MagicMock()
    get_resp.json.return_value = [{"id": "user-uuid"}]
    get_resp.raise_for_status.return_value = None

    put_resp = MagicMock()
    put_resp.status_code = 400
    put_resp.json.return_value = {
        "error": "invalid_parameter"
    }  # no password/policy content
    put_resp.raise_for_status.side_effect = Exception("400 Bad Request")

    with patch.object(cr.requests, "get", return_value=get_resp), patch.object(
        cr.requests, "put", return_value=put_resp
    ):
        with pytest.raises(Exception, match="400 Bad Request"):
            cr._reset_system_user_password("host", 443, "token", "bad-password")


# --- _run_fallback -------------------------------------------------------------


def test_run_fallback_calls_oidc_update_and_system_user_reset():
    with patch.object(
        cr, "_get_service_token", return_value="svc-token"
    ) as mock_token, patch.object(
        cr, "_update_oidc_client_secret"
    ) as mock_oidc, patch.object(
        cr, "_reset_system_user_password"
    ) as mock_reset:
        cr._run_fallback("host", 443, "svc-secret", "oidc-secret", "sys-password")

    mock_token.assert_called_once_with("host", 443, "svc-secret")
    mock_oidc.assert_called_once_with("host", 443, "svc-token", "oidc-secret")
    mock_reset.assert_called_once_with("host", 443, "svc-token", "sys-password")


# --- _SERVICE_ACCOUNT_ROLES ---------------------------------------------------


def test_service_account_roles_includes_manage_clients():
    assert "manage-clients" in cr._SERVICE_ACCOUNT_ROLES


def test_service_account_roles_includes_runtime_roles():
    for role in ("manage-users", "query-users", "query-groups", "view-realm"):
        assert role in cr._SERVICE_ACCOUNT_ROLES
