"""
Unit test for the kaapana-backend UserService auth changeover (#1918).

Guards that UserService logs in via the kaapana-service client
(client_credentials) against the kaapana realm — not the old admin
username/password against master. python-keycloak is stubbed so no live
Keycloak is needed.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Make the app package importable and stub python-keycloak (not installed here).
FILES_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FILES_DIR))

keycloak_stub = MagicMock()
sys.modules.setdefault("keycloak", keycloak_stub)
keycloak_exc = MagicMock()
keycloak_exc.KeycloakGetError = type("KeycloakGetError", (Exception,), {})
sys.modules.setdefault("keycloak.exceptions", keycloak_exc)

import app.users.services as services  # noqa: E402


def test_login_uses_service_client_credentials_in_kaapana_realm():
    services.KeycloakAdmin.reset_mock()

    services.UserService(
        server_url="https://keycloak-internal-service.admin.svc/auth/",
        client_secret="s3cr3t",
    )

    assert services.KeycloakAdmin.called
    _, kwargs = services.KeycloakAdmin.call_args

    assert kwargs["client_id"] == "kaapana-service"
    assert kwargs["client_secret_key"] == "s3cr3t"
    assert kwargs["realm_name"] == "kaapana"
    assert kwargs["user_realm_name"] == "kaapana"  # not "master"
    # the old admin password grant args must be gone
    assert "username" not in kwargs and "password" not in kwargs
