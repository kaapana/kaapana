"""
Behavioral test for handle-secret.sh (the cert-init image, ACTION=remove hook).

The pre-delete hook must delete an existing certificate secret in both namespaces;
otherwise the next deploy reuses the old hostname's certificate. kubectl is replaced
by a stub that records its calls and reports the secret as present.

Run from anywhere:
    pytest services/kaapana-admin/admin-init/tests/test_handle_secret.py
"""

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "docker" / "handle-secret.sh"


def run_remove(tmp_path, kubectl_mock_logic):
    log = tmp_path / "kubectl.log"
    kubectl = tmp_path / "kubectl"
    kubectl.write_text(f'#!/bin/sh\necho "$*" >> "{log}"\n{kubectl_mock_logic}')
    kubectl.chmod(0o755)

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        env={
            **os.environ,
            "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
            "ACTION": "remove",
            "SECRET_NAME": "certificate",
            "SECRET_NAMESPACE": "services",
            "ADMIN_NAMESPACE": "admin",
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result, log.read_text() if log.exists() else ""


def test_remove_deletes_existing_secret_in_both_namespaces(tmp_path):
    result, calls = run_remove(tmp_path, "exit 0\n")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "-n services delete secret certificate" in calls
    assert "-n admin delete secret certificate" in calls


def test_remove_succeeds_when_secret_is_already_gone(tmp_path):
    """Like real kubectl, deleting a missing secret only exits 0 with --ignore-not-found."""
    result, calls = run_remove(
        tmp_path,
        'case "$*" in\n'
        "  *'get secret'*) exit 1 ;;\n"
        "  *'delete secret'*--ignore-not-found*) exit 0 ;;\n"
        "  *'delete secret'*) exit 1 ;;\n"
        "esac\nexit 0\n",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "-n services delete secret certificate" in calls
    assert "-n admin delete secret certificate" in calls
