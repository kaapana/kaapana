"""Network suite: speedtest from inside the cluster.

The ingest sender reaches the platform over this same link, so a shift here
moves the ingestion numbers with it.
"""

from __future__ import annotations

import json
import os

from .. import kubectl
from ..model import HIGHER_IS_BETTER, Metric, Sample

NAME = "internet"
POD_NAME = "benchmark-speedtest"
IMAGE = "jadcock/speedtest-cli"
NAMESPACE = "default"
TIMEOUT_S = 300
NO_PROXY = "localhost,127.0.0.1,169.254.169.254,dkfz-heidelberg.de,10.1.0.0/16,10.152.183.0/24"

METRICS = {
    "ping_seconds": Metric("network_ping_seconds", "seconds"),
    "download_bits_per_second": Metric(
        "network_download_bits_per_second", "bits_per_second", HIGHER_IS_BETTER),
    "upload_bits_per_second": Metric(
        "network_upload_bits_per_second", "bits_per_second", HIGHER_IS_BETTER),
}


def run(target) -> list[Sample]:
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    environment = [
        {"name": "https_proxy", "value": proxy},
        {"name": "http_proxy", "value": proxy},
        {"name": "no_proxy", "value": NO_PROXY},
    ] if proxy else []
    manifest = json.dumps({
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": POD_NAME, "namespace": NAMESPACE},
        "spec": {
            "restartPolicy": "Never",
            "containers": [{
                "name": "speedtest",
                "image": IMAGE,
                "imagePullPolicy": "IfNotPresent",
                "command": ["python3", "-u", "/speedtest.py", "--json"],
                "env": environment,
            }],
        },
    })
    logs = kubectl.run_pod(target.kubectl, manifest, POD_NAME, NAMESPACE, TIMEOUT_S)
    report = json.loads(next(line for line in reversed(logs.splitlines()) if line.startswith("{")))
    values = {
        "ping_seconds": round(report["ping"] / 1000, 4),
        "download_bits_per_second": round(report["download"]),
        "upload_bits_per_second": round(report["upload"]),
    }
    return [Sample("cluster", METRICS[key], value) for key, value in values.items()]
