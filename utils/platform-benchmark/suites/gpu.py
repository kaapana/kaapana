"""GPU suite: run gpu_burn (utils/nvidia-benchmark.yaml) as a pod on the
instance's cluster and parse throughput + per-GPU verdicts from its logs."""

from __future__ import annotations

import json
import re

from suites.k8s import run_pod

POD_NAME = "benchmark-gpu-burn"
IMAGE = "chrstnhntschl/gpu_burn:latest"


def manifest(namespace: str, seconds: int) -> str:
    return json.dumps({
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": POD_NAME, "namespace": namespace},
        "spec": {
            "restartPolicy": "Never",
            "containers": [{
                "name": "gpu-burn",
                "image": IMAGE,
                "args": [str(seconds)],
            }],
        },
    })


def run(kubectl: str, namespace: str, seconds: int = 60) -> dict:
    logs = run_pod(kubectl, manifest(namespace, seconds), POD_NAME, namespace,
                   timeout_s=seconds + 240)
    gflops = [float(m) for m in re.findall(r"\(([\d.]+) Gflop/s\)", logs)]
    # gpu_burn progress lines report "errors: 0 - 0" (one number per GPU)
    errors = [
        int(n)
        for m in re.findall(r"errors:((?:\s+\d+(?:\s+-)?)+)", logs)
        for n in re.findall(r"\d+", m)
    ]
    if not gflops:
        raise RuntimeError(f"no Gflop/s readings in gpu_burn output:\n{logs[-2000:]}")
    return {
        "burn_seconds": seconds,
        "gflops_max": round(max(gflops)),
        "gpus_ok": len(re.findall(r"GPU \d+: OK", logs)),
        "gpus_faulty": len(re.findall(r"GPU \d+: FAULTY", logs)),
        "errors": max(errors) if errors else 0,
    }
