"""
Behavioral tests for bootstrap_admin_client.py.

Guards the admin-client-first bootstrap: if the kaapana-admin client already
authenticates, the bootstrap is a no-op; otherwise it is created in the master
realm and granted the master 'admin' role. No live Keycloak: HTTP is mocked.

Run from anywhere:
    pytest services/kaapana-admin/keycloak/keycloak-setup/tests/test_bootstrap_admin_client.py
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

FILES_DIR = Path(__file__).resolve().parent.parent / "docker" / "files"
sys.path.insert(0, str(FILES_DIR))

# Stub local modules not installed in the test environment
sys.modules.setdefault("KeycloakHelper", MagicMock())
sys.modules.setdefault("logger", MagicMock())

import bootstrap_admin_client as boot  # noqa: E402


# --- _admin_client_functional -------------------------------------------------


def test_admin_client_functional_true_on_200():
    resp = MagicMock()
    resp.status_code = 200
    with patch.object(boot.requests, "post", return_value=resp) as mock_post:
        assert boot._admin_client_functional("host", 443, "secret") is True

    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    url = mock_post.call_args[0][0]
    data = kwargs["data"]
    assert data["grant_type"] == "client_credentials"
    assert data["client_id"] == "kaapana-admin"
    assert "/realms/master/protocol/openid-connect/token" in url


def test_admin_client_functional_false_on_401():
    resp = MagicMock()
    resp.status_code = 401
    with patch.object(boot.requests, "post", return_value=resp):
        assert boot._admin_client_functional("host", 443, "secret") is False


def test_admin_client_functional_false_on_exception():
    with patch.object(boot.requests, "post", side_effect=Exception("refused")):
        assert boot._admin_client_functional("host", 443, "secret") is False


# --- _create_admin_client -----------------------------------------------------


def test_create_admin_client_creates_and_grants_master_admin_role():
    kc = MagicMock()
    kc.auth_url = "https://h:443/auth/admin/realms/"

    sa_resp = MagicMock()
    sa_resp.json.return_value = {"id": "sa-user-id"}
    role_resp = MagicMock()
    role_resp.json.return_value = {"name": "admin", "id": "role-id"}

    def fake_request(url, request=None, *args, **kwargs):
        if url.endswith("service-account-user"):
            return sa_resp
        if url.endswith("master/roles/admin"):
            return role_resp
        return MagicMock()

    kc.make_authorized_request.side_effect = fake_request

    # Client missing on first lookup, present on the second (after creation).
    with patch.object(
        boot, "_get_master_client_uuid", side_effect=[None, "client-uuid"]
    ):
        boot._create_admin_client(kc, "secret123")

    calls = kc.make_authorized_request.call_args_list
    urls = [c.args[0] for c in calls]

    # Client was created in the master realm with the persisted secret.
    create_calls = [c for c in calls if c.args[0].endswith("master/clients")]
    assert create_calls, "expected a POST to master/clients"
    assert any(
        len(c.args) >= 3 and c.args[2].get("secret") == "secret123"
        for c in create_calls
    )

    # master 'admin' realm role was assigned to the service account.
    assert any("master/users/sa-user-id/role-mappings/realm" in u for u in urls)


def test_create_admin_client_updates_existing_client():
    kc = MagicMock()
    kc.auth_url = "https://h:443/auth/admin/realms/"

    sa_resp = MagicMock()
    sa_resp.json.return_value = {"id": "sa-user-id"}
    role_resp = MagicMock()
    role_resp.json.return_value = {"name": "admin"}

    def fake_request(url, request=None, *args, **kwargs):
        if url.endswith("service-account-user"):
            return sa_resp
        if url.endswith("master/roles/admin"):
            return role_resp
        return MagicMock()

    kc.make_authorized_request.side_effect = fake_request

    with patch.object(boot, "_get_master_client_uuid", return_value="existing-uuid"):
        boot._create_admin_client(kc, "secret123")

    urls = [c.args[0] for c in kc.make_authorized_request.call_args_list]
    # Existing client is updated via its UUID, not created fresh.
    assert any(u.endswith("master/clients/existing-uuid") for u in urls)
