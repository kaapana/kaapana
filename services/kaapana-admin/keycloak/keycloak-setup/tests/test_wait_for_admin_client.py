"""
Behavioral test for wait_for_admin_client.py (the setup-job initContainer).

A failed bootstrap must make the init container exit non-zero (the Pod fails
visibly) instead of polling forever. With ADMIN_CLIENT_WAIT_TIMEOUT=0 the wait
loop is skipped entirely, so the script fails fast without any network call.

Run from anywhere:
    pytest services/kaapana-admin/keycloak/keycloak-setup/tests/test_wait_for_admin_client.py
"""

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "docker"
    / "files"
    / "wait_for_admin_client.py"
)


def test_exits_non_zero_when_admin_client_never_ready():
    result = subprocess.run(
        [sys.executable, "-u", str(SCRIPT)],
        env={
            **os.environ,
            "KEYCLOAK_HOST": "keycloak.invalid",
            "KAAPANA_ADMIN_CLIENT_SECRET": "dummy",
            "ADMIN_CLIENT_WAIT_TIMEOUT": "0",
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1, (
        f"expected exit 1 on bootstrap failure, got {result.returncode}; "
        f"stderr: {result.stderr}"
    )
    assert "never became ready" in result.stdout
