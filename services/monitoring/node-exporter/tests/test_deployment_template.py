"""
Unit test for the node-exporter chart's host-root mount.

Guards that the hostPath "/" mount receives no mount propagation from the host:
with HostToContainer every kubelet subPath bind-mount propagates into node-exporter's
long-lived mount namespace and is pinned there, so the kubelet cannot clean up the
orphaned pod and new pods end up stuck Pending (#2241). No Helm needed - the template
is read as YAML with its Helm expressions replaced by a placeholder.
"""

import re
from pathlib import Path

import yaml

TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "node-exporter-chart/templates/deployment.yaml"
)


def test_host_root_mount_receives_no_host_mount_propagation():
    text = re.sub(r"\{\{.*?\}\}", "PLACEHOLDER", TEMPLATE.read_text())
    containers = yaml.safe_load(text)["spec"]["template"]["spec"]["containers"]
    exporter = next(c for c in containers if c["name"] == "node-exporter")
    root = next(m for m in exporter["volumeMounts"] if m["mountPath"] == "/host/root")
    # Kubernetes defaults to None; anything else lets host mounts flow in.
    assert root.get("mountPropagation", "None") == "None"
