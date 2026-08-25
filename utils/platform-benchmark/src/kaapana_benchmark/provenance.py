"""What the benchmark ran on and against.

A bigger node, a different dataset revision or a different platform version can
all look like a code change. Every capture degrades to an "error" entry rather
than failing the run.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import kubectl


def _command(*argv: str) -> str:
    return subprocess.run(argv, capture_output=True, text=True,
                          timeout=30, check=False).stdout.strip()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git(repo: Path) -> dict:
    return {
        "commit": _command("git", "-C", str(repo), "rev-parse", "HEAD"),
        "branch": _command("git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(_command("git", "-C", str(repo), "status", "--porcelain")),
    }


def _ci() -> dict:
    """Present only inside GitLab CI; empty locally."""
    variables = {
        "pipeline_id": "CI_PIPELINE_ID",
        "pipeline_url": "CI_PIPELINE_URL",
        "job_id": "CI_JOB_ID",
        "job_url": "CI_JOB_URL",
        "commit_ref": "CI_COMMIT_REF_NAME",
        "merge_request_iid": "CI_MERGE_REQUEST_IID",
        "runner": "CI_RUNNER_DESCRIPTION",
    }
    return {key: os.environ[name] for key, name in variables.items() if os.environ.get(name)}


def _runner(scratch: Path) -> dict:
    info = {
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "kernel": platform.release(),
        "dcmtk": _command("dcmsend", "--version").splitlines()[0]
                 if shutil.which("dcmsend") else None,
        "disk_total_gb": round(shutil.disk_usage(scratch).total / 2**30, 1),
    }
    meminfo = Path("/proc/meminfo").read_text().splitlines()
    kilobytes = int(next(x for x in meminfo if x.startswith("MemTotal:")).split()[1])
    info["memory_gb"] = round(kilobytes / 2**20, 1)
    cpuinfo = Path("/proc/cpuinfo").read_text().splitlines()
    info["cpu_model"] = next(
        x.split(":", 1)[1].strip() for x in cpuinfo if x.startswith("model name")
    )
    return info


def _cluster(kubectl_prefix: str) -> dict:
    nodes = json.loads(kubectl.run(kubectl_prefix, "get", "nodes", "-o", "json"))["items"]
    return {
        "nodes": [
            {
                "name": node["metadata"]["name"],
                "cpu": node["status"]["capacity"].get("cpu"),
                "memory": node["status"]["capacity"].get("memory"),
                "gpus": node["status"]["capacity"].get("nvidia.com/gpu", "0"),
                "os_image": node["status"]["nodeInfo"].get("osImage"),
                "kernel": node["status"]["nodeInfo"].get("kernelVersion"),
                "kubelet": node["status"]["nodeInfo"].get("kubeletVersion"),
            }
            for node in nodes
        ]
    }


def _dataset(data_dir: Path | None, scenarios: Path | None) -> dict:
    if data_dir is None:
        return {}
    described = {"path": str(data_dir),
                 "commit": _command("git", "-C", str(data_dir), "rev-parse", "HEAD")}
    if scenarios and Path(scenarios).is_file():
        described["scenarios_file"] = str(scenarios)
        described["scenarios"] = json.loads(Path(scenarios).read_text())
    return described


def collect(target, repo: Path, profile: str) -> dict:
    """*profile* names the class of environment (ci-vm, workstation)."""
    context = {
        "profile": profile,
        "collected_at": now(),
        "target": {"host": target.host, "kubectl": target.kubectl},
    }
    for key, capture in (
        ("code", lambda: _git(repo)),
        ("ci", _ci),
        ("runner", lambda: _runner(repo)),
        ("cluster", lambda: _cluster(target.kubectl)),
        ("dataset", lambda: _dataset(target.data_dir, target.scenarios)),
    ):
        try:
            context[key] = capture()
        except Exception as error:
            context[key] = {"error": str(error)}
    return context
