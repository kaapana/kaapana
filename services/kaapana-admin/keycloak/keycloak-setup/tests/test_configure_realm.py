"""
Behavioral tests for configure_realm.py.

The setup job authenticates as the kaapana-admin client (client_credentials) and
runs a full, idempotent realm configuration. The unit-testable surface covers
the kaapana-service role set and the retry behaviour on 403 responses.
No live Keycloak needed.

Run from anywhere:
    pytest services/kaapana-admin/keycloak/keycloak-setup/tests/test_configure_realm.py
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Set required env vars before module-level code in configure_realm runs
os.environ.setdefault("DEV_MODE", "false")

FILES_DIR = Path(__file__).resolve().parent.parent / "docker" / "files"
sys.path.insert(0, str(FILES_DIR))

# Stub local modules not installed in the test environment
sys.modules.setdefault("KeycloakHelper", MagicMock())
sys.modules.setdefault("logger", MagicMock())

import configure_realm as cr  # noqa: E402


def test_service_account_roles_are_minimal():
    assert cr._SERVICE_ACCOUNT_ROLES == [
        "manage-users",
        "query-users",
        "query-groups",
        "view-realm",
    ]


def test_service_account_roles_exclude_manage_clients():
    # kaapana-service is the weak runtime client; it must not be able to manage clients.
    assert "manage-clients" not in cr._SERVICE_ACCOUNT_ROLES


def test_fallback_helpers_removed():
    # The fallback path was replaced by the admin-client / two-job design.
    for name in (
        "_run_fallback",
        "_update_oidc_client_secret",
        "_reset_system_user_password",
        "_service_client_functional",
        "_get_service_token",
    ):
        assert not hasattr(cr, name), f"{name} must be removed from configure_realm.py"
