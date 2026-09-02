"""Runs utils/recover_data.sh against a fake kubectl and a temp data dir to check
that a surviving hostpath directory is bound statically to a recreated claim."""

import os
import subprocess
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "utils/recover_data.sh"

# Records every applied manifest; answers "no releases", "no PVs" and "no PVC".
FAKE_KUBECTL = """#!/bin/bash
case "$*" in
  "get secrets"*) exit 0 ;;
  "get pv -o json") echo '{"items":[]}' ;;
  "get pvc "*) exit 1 ;;
  "apply -f -") { echo "---"; cat; } >> "$APPLIED" ;;
  *) echo "unexpected kubectl call: $*" >&2; exit 2 ;;
esac
"""


def test_surviving_directory_is_bound_to_recreated_claim(tmp_path):
    data_dir = tmp_path / "kaapana"
    minio_dir = data_dir / "services-minio-pv-claim-pvc-0a1b2c3d"
    minio_dir.mkdir(parents=True)
    (data_dir / "jip-project-admin-models-pv-claim-pvc-4e5f6a7b").mkdir()
    (data_dir / "project-test-p1-workflow-data-pv-claim-pvc-2b3c4d5e").mkdir()  # 0.6.x: dashed id, no prefix
    (data_dir / "services-jupyterlab-xyz-pv-claim-pvc-8c9d0e1f").mkdir()  # extension, unknown owner
    (data_dir / "services-my-extension-data-pv-claim-pvc-6f7a8b9c").mkdir()  # extension listed in claims file
    claims = tmp_path / "claims.conf"
    claims.write_text("# extension claims\nservices/my-extension-data-pv-claim fast 1Gi my-extension admin\n")
    kubectl = tmp_path / "kubectl"
    kubectl.write_text(FAKE_KUBECTL)
    kubectl.chmod(0o755)
    applied = tmp_path / "applied.yaml"

    result = subprocess.run(
        [str(SCRIPT), "--fast-dir", str(data_dir), "--slow-dir", str(data_dir), "--platform-prefix", "jip"]
        + ["--claims-file", str(claims)],
        env={**os.environ, "KUBECTL": str(kubectl), "APPLIED": str(applied)},
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    docs = {(d["kind"], d["metadata"]["name"]): d for d in yaml.safe_load_all(applied.read_text()) if d}

    pv = docs[("PersistentVolume", minio_dir.name)]
    assert pv["spec"]["hostPath"]["path"] == str(minio_dir)
    assert pv["spec"]["persistentVolumeReclaimPolicy"] == "Retain"
    assert pv["spec"]["claimRef"] == {"namespace": "services", "name": "minio-pv-claim"}
    pvc = docs[("PersistentVolumeClaim", "minio-pv-claim")]
    assert pvc["spec"]["volumeName"] == minio_dir.name
    assert pvc["spec"]["storageClassName"] == "kaapana-hostpath-slow-data-dir"
    assert pvc["metadata"]["annotations"]["meta.helm.sh/release-name"] == "kaapana-platform-chart"
    # project namespaces are owned by a release named like the namespace
    project_ns = docs[("Namespace", "jip-project-admin")]
    assert project_ns["metadata"]["annotations"]["meta.helm.sh/release-name"] == "jip-project-admin"
    assert docs[("PersistentVolumeClaim", "workflow-data-pv-claim")]["metadata"]["namespace"] == "project-test-p1"
    assert ("PersistentVolumeClaim", "jupyterlab-xyz-pv-claim") not in docs
    # a claims-file row hands the claim to the extension's release, the namespace stays with the platform
    extension_pvc = docs[("PersistentVolumeClaim", "my-extension-data-pv-claim")]
    assert extension_pvc["metadata"]["annotations"]["meta.helm.sh/release-name"] == "my-extension"
    assert extension_pvc["spec"]["storageClassName"] == "kaapana-hostpath-fast-data-dir"
    assert docs[("Namespace", "services")]["metadata"]["annotations"]["meta.helm.sh/release-name"] == "kaapana-platform-chart"
    assert "Recovered (4):" in result and "Skipped (1):" in result
