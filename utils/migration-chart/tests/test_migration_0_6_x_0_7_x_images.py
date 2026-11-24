"""
The 0.6.x -> 0.7.x migration starts its PostgreSQL dump and restore pods from the platform's
registry only: a server without access to Docker Hub can pull nothing else. No cluster: kubectl is
a stub on PATH that records every manifest and reports each pod as finished.

Run from anywhere:
    pytest utils/migration-chart/tests/test_migration_0_6_x_0_7_x_images.py
"""

import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "utils/migration-chart/docker/files/migration-0.6.x-0.7.x.sh"
CHART = ROOT / "utils/migration-chart/migration-chart/templates/migration.yaml"
# The Dockerfiles of the two images the chart hands to the script.
DOCKERFILES = (
    ROOT / "utils/migration-chart/docker/postgres-17/Dockerfile",
    ROOT / "services/kaapana-admin/postgres/docker/Dockerfile",
)

# Without the old admin project namespace the script ends after the database upgrade.
KUBECTL = """#!/bin/bash
case "$*" in
  apply*) cat >> "$APPLIED" ;;
  "get pod "*) echo Succeeded ;;
  "get namespace "*) exit 1 ;;
esac
"""


def test_dump_and_restore_pods_come_from_the_platform_registry(tmp_path):
    (tmp_path / "kubectl").write_text(KUBECTL)
    (tmp_path / "kubectl").chmod(0o755)
    cluster = tmp_path / "fast" / "admin-keycloak-pv-claim-pvc-1234" / "data"
    cluster.mkdir(parents=True)
    (cluster / "PG_VERSION").write_text("17\n")
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", APPLIED=str(tmp_path / "applied"))
    env.update(
        STORAGE_PROVIDER="microk8s.io/hostpath", STORAGE_CLASS_WORKFLOW="wf", ADMIN_NAMESPACE="admin",
        PLATFORM_PREFIX="kaapana", FAST_DATA_DIR=str(tmp_path / "fast"),
        MIGRATION_IMAGE="registry.example/migration:1",
        PG17_IMAGE="registry.example/migration-postgres-17:1",
        PG18_IMAGE="registry.example/postgres-18.4-alpine:1",
    )
    result = subprocess.run(["bash", str(SCRIPT)], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    pods = (tmp_path / "applied").read_text()
    assert re.findall(r"^ *image: (\S+)$", pods, re.M) == [env["PG17_IMAGE"], env["PG18_IMAGE"]]
    assert pods.count("imagePullSecrets: [{name: registry-secret}]") == 2


def test_the_chart_pulls_every_image_it_hands_to_the_script():
    """The build ships only images a chart names on an `image:` line, and the job's init
    containers pull them before the script touches a database."""
    chart = CHART.read_text()
    pulled = set(re.findall(r'^ *image: "(.+)"$', chart, re.M))
    handed = dict(re.findall(r'- name: (PG1[78]_IMAGE)\n *value: "(.+)"', chart))
    assert set(handed) == {"PG17_IMAGE", "PG18_IMAGE"}
    assert set(handed.values()) <= pulled
    built = {name for f in DOCKERFILES for name in re.findall(r'^LABEL IMAGE="(.+)"$', f.read_text(), re.M)}
    assert {value.rsplit("/", 1)[1].split(":")[0] for value in handed.values()} == built
