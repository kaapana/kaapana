"""
Behavioral test for store_certs_in_tls_volume in kaapanactl.sh (--install-certs).

cert-init installs certificate files only from the tls-pv-claim volume, so
--install-certs must copy them into that volume's host folder, or warn when the
storage has none. install_certs itself needs root, so the test extracts only this
function and runs it with a microk8s.kubectl stub that answers the claim and PV
queries.

Run from anywhere:
    pytest services/kaapana-admin/admin-init/tests/test_install_certs.py
"""

import os
import subprocess
from pathlib import Path

KAAPANACTL = Path(__file__).resolve().parents[4] / "kaapanactl.sh"
FUNCTION = "store_certs_in_tls_volume"


def extract_function():
    text = KAAPANACTL.read_text()
    start = text.index(f"function {FUNCTION} {{")
    end = text.index("\n}\n", start) + 3
    return text[start:end]


def run_store(tmp_path, pvc_volume, pv_host_path):
    """pvc_volume/pv_host_path None: the stub fails that query like a missing object."""
    work = tmp_path / "work"
    work.mkdir()
    (work / "tls.crt").write_text("CERT\n")
    (work / "tls.key").write_text("KEY\n")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pvc_answer = "exit 1" if pvc_volume is None else f"printf %s '{pvc_volume}'"
    pv_answer = "exit 1" if pv_host_path is None else f"printf %s '{pv_host_path}'"
    kubectl = bin_dir / "microk8s.kubectl"
    kubectl.write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        f"  *'get pvc tls-pv-claim'*) {pvc_answer} ;;\n"
        f"  *'get pv '*) {pv_answer} ;;\n"
        "  *) exit 1 ;;\n"
        "esac\n"
    )
    kubectl.chmod(0o755)

    # kaapanactl.sh's own shell options: a failing query must not end it early.
    script = "set -euf -o pipefail\n"
    script += f'YELLOW=""; NC=""; ADMIN_NAMESPACE=admin\n{extract_function()}\n'
    script += f"{FUNCTION}\n"
    return subprocess.run(
        ["bash", "-c", script],
        cwd=work,
        env={**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_hostpath_volume_receives_both_files(tmp_path):
    volume = tmp_path / "admin-tls-pv-claim-pvc-1"
    volume.mkdir()

    result = run_store(tmp_path, "pvc-1", str(volume))

    assert result.returncode == 0, result.stdout + result.stderr
    assert (volume / "tls.crt").read_text() == "CERT\n"
    assert (volume / "tls.key").read_text() == "KEY\n"
    assert (volume / "tls.key").stat().st_mode & 0o777 == 0o600
    assert str(volume) in result.stdout
    assert "Warning" not in result.stdout


def test_volume_without_host_path_warns_and_writes_nothing(tmp_path):
    result = run_store(tmp_path, "pvc-1", "")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "not stored for the next deploy" in result.stdout
    assert "run --install-certs again" in result.stdout
    files = sorted(
        str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*") if p.is_file()
    )
    assert files == ["bin/microk8s.kubectl", "work/tls.crt", "work/tls.key"]


def test_missing_claim_warns(tmp_path):
    result = run_store(tmp_path, None, None)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "not stored for the next deploy" in result.stdout
