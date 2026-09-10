"""
Behavioral tests for migration-0.5.x-0.6.x.sh.

Guards what the migration leaves behind for the follow-up install: the admin
namespace is annotated for the release named in ADMIN_RELEASE_NAME, the services
namespace for Helm namespace "default", and a PVC whose data cannot be migrated
fails the job. No cluster: kubectl is a stub on PATH recording every manifest.

Run from anywhere:
    pytest utils/migration-chart/tests/test_migration_0_5_x_0_6_x.py
"""

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "docker" / "files" / "migration-0.5.x-0.6.x.sh"

# Records applied manifests, reports pods running and claims bound, and knows no
# volume for tls-pv-claim so that one data migration fails.
KUBECTL = """#!/bin/bash
case "$*" in
  apply*) cat >> "$APPLIED" ;;
  "get pod "*) echo Running ;;
  *volumeName*) [[ "$*" == *tls-pv-claim* ]] || echo pv-x ;;
  *hostPath*) echo /nonexistent ;;
  *status.phase*) echo Bound ;;
esac
"""


def _run(tmp_path):
    (tmp_path / "kubectl").write_text(KUBECTL)
    (tmp_path / "kubectl").chmod(0o755)
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", APPLIED=str(tmp_path / "applied"))
    env.update(
        STORAGE_PROVIDER="microk8s.io/hostpath", STORAGE_CLASS_SLOW="slow", STORAGE_CLASS_FAST="fast",
        STORAGE_CLASS_WORKFLOW="wf", SERVICES_NAMESPACE="services", ADMIN_NAMESPACE="admin",
        ADMIN_RELEASE_NAME="custom-admin-chart", VOLUME_SLOW_DATA="1Gi", MIGRATION_IMAGE="img",
        FAST_DATA_DIR=str(tmp_path / "fast"), SLOW_DATA_DIR=str(tmp_path / "slow"),
    )
    result = subprocess.run(["bash", str(SCRIPT)], cwd=tmp_path, env=env, capture_output=True, text=True)
    return result, (tmp_path / "applied").read_text()


def test_namespaces_are_owned_by_the_releases_the_deploy_installs(tmp_path):
    _, applied = _run(tmp_path)
    assert "name: admin\n" in applied
    assert "meta.helm.sh/release-name: custom-admin-chart\n" in applied
    assert "meta.helm.sh/release-name: kaapana-admin-chart" not in applied
    services = applied.split("name: services\n", 1)[1]
    assert services.startswith("  labels:") and "release-namespace: default\n" in services.split("---")[0]


def test_failed_pvc_migration_fails_the_job(tmp_path):
    result, _ = _run(tmp_path)
    assert "tls-pv-claim:ERROR" in result.stdout
    assert result.returncode != 0
