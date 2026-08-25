"""GPU suite: gpu_burn on every GPU of the cluster."""

from __future__ import annotations

import json
import re

from .. import kubectl
from ..model import HIGHER_IS_BETTER, NO_DIRECTION, Metric, Sample

NAME = "gpu"
POD_NAME = "benchmark-gpu-burn"
IMAGE = "chrstnhntschl/gpu_burn:latest"
NAMESPACE = "default"
BURN_SECONDS = 60
STARTUP_ALLOWANCE_S = 240

METRICS = {
    "gflops": Metric("gpu_gflops", "gflops", HIGHER_IS_BETTER),
    "healthy_count": Metric("gpu_healthy_count", "", HIGHER_IS_BETTER),
    "faulty_count": Metric("gpu_faulty_count", "", NO_DIRECTION, invalidates_case=True),
}

GFLOPS_PATTERN = re.compile(r"\(([\d.]+) Gflop/s\)")


def run(target) -> list[Sample]:
    manifest = json.dumps({
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": POD_NAME, "namespace": NAMESPACE},
        "spec": {
            "restartPolicy": "Never",
            "containers": [{"name": "gpu-burn", "image": IMAGE, "args": [str(BURN_SECONDS)]}],
        },
    })
    logs = kubectl.run_pod(
        target.kubectl, manifest, POD_NAME, NAMESPACE, BURN_SECONDS + STARTUP_ALLOWANCE_S
    )
    readings = [float(value) for value in GFLOPS_PATTERN.findall(logs)]
    if not readings:
        raise RuntimeError(f"gpu_burn reported no throughput:\n{logs[-2000:]}")
    values = {
        "gflops": round(max(readings)),
        "healthy_count": len(re.findall(r"GPU \d+: OK", logs)),
        "faulty_count": len(re.findall(r"GPU \d+: FAULTY", logs)),
    }
    return [Sample("cluster", METRICS[key], value) for key, value in values.items()]
