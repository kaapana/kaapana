"""Renders kaapana-storage-chart with helm to check that the reclaim policy of the
hostpath StorageClasses can be switched to Retain (it used to be hardcoded to Delete)."""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

STORAGE_CHART = Path(__file__).resolve().parents[1] / "utils/kaapana-storage-chart"


@pytest.mark.skipif(shutil.which("helm") is None, reason="helm is not installed")
def test_hostpath_reclaim_policy_can_be_set_to_retain():
    rendered = subprocess.run(
        ["helm", "template", "storage", str(STORAGE_CHART)]
        + ["--set", "global.hostpath_reclaim_policy=Retain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    hostpath_classes = [
        doc
        for doc in yaml.safe_load_all(rendered)
        if doc and doc.get("provisioner") == "microk8s.io/hostpath"
    ]
    assert len(hostpath_classes) == 2
    assert all(doc["reclaimPolicy"] == "Retain" for doc in hostpath_classes)
