"""Best-effort hardware/environment snapshot, stored alongside a benchmark
result so a comparison between tags can be read next to what it ran on —
otherwise a run on a bigger node can masquerade as a performance win.

Never raises: any capture failure (no kubectl access, no GPUs, non-Linux
runner, ...) degrades to an "error" key instead of failing the benchmark
run that asked for it.
"""

from __future__ import annotations

import json
import os
import shutil

from suites.k8s import sh


def _runner() -> dict:
    info: dict = {"cpu_count": os.cpu_count()}
    total, _, _ = shutil.disk_usage(os.path.dirname(__file__))
    info["disk_total_gb"] = round(total / 2**30, 1)
    try:
        with open("/proc/meminfo") as f:
            kb = int(next(line for line in f if line.startswith("MemTotal:")).split()[1])
        info["mem_total_gb"] = round(kb / 2**20, 1)
    except (OSError, StopIteration):
        pass
    try:
        with open("/proc/cpuinfo") as f:
            info["cpu_model"] = next(
                line.split(":", 1)[1].strip() for line in f if line.startswith("model name"))
    except (OSError, StopIteration):
        pass
    return info


def _cluster(kubectl: str) -> dict:
    nodes = json.loads(sh(kubectl, "get", "nodes", "-o", "json"))["items"]
    return {"nodes": [
        {
            "name": node["metadata"]["name"],
            "cpu": node["status"].get("capacity", {}).get("cpu"),
            "memory": node["status"].get("capacity", {}).get("memory"),
            "gpus": node["status"].get("capacity", {}).get("nvidia.com/gpu"),
            "os_image": node["status"].get("nodeInfo", {}).get("osImage"),
            "kernel_version": node["status"].get("nodeInfo", {}).get("kernelVersion"),
            "kubelet_version": node["status"].get("nodeInfo", {}).get("kubeletVersion"),
        }
        for node in nodes
    ]}


def collect(kubectl: str = "kubectl") -> dict:
    """Runner-local info (cpu/mem/disk of the machine running the benchmark)
    plus the target cluster's node capacity/versions, via the same
    configurable kubectl entrypoint the internet/gpu/helm suites use."""
    info: dict = {}
    try:
        info["runner"] = _runner()
    except Exception as e:
        info["runner"] = {"error": str(e)}
    try:
        info["cluster"] = _cluster(kubectl)
    except Exception as e:
        info["cluster"] = {"error": str(e)}
    return info
