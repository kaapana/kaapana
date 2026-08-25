"""Cluster access through a configurable command prefix.

The prefix is anything that behaves like kubectl — "kubectl",
"microk8s kubectl", or "ssh <host> microk8s kubectl" for a remote instance.
"""

from __future__ import annotations

import shlex
import subprocess
import time

POD_POLL_SECONDS = 5


def run(prefix: str, *args: str, stdin: str | None = None) -> str:
    process = subprocess.run(
        shlex.split(prefix) + list(args),
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(f"{prefix} {' '.join(args)} failed: {process.stderr.strip()}")
    return process.stdout


def _pod_phase(prefix: str, name: str, namespace: str) -> str:
    return run(
        prefix, "get", "pod", name, "-n", namespace, "-o", "jsonpath={.status.phase}"
    ).strip()


def run_pod(prefix: str, manifest: str, name: str, namespace: str, timeout_s: int) -> str:
    """Run a pod to completion and return its logs. Always deletes the pod."""
    run(prefix, "delete", "pod", name, "-n", namespace, "--ignore-not-found", "--wait=true")
    run(prefix, "apply", "-n", namespace, "-f", "-", stdin=manifest)
    try:
        deadline = time.time() + timeout_s
        phase = _pod_phase(prefix, name, namespace)
        while phase not in ("Succeeded", "Failed"):
            if time.time() > deadline:
                raise TimeoutError(f"pod {name} still in phase {phase!r} after {timeout_s}s")
            time.sleep(POD_POLL_SECONDS)
            phase = _pod_phase(prefix, name, namespace)
        logs = run(prefix, "logs", name, "-n", namespace)
        if phase == "Failed":
            raise RuntimeError(f"pod {name} failed:\n{logs[-2000:]}")
        return logs
    finally:
        run(prefix, "delete", "pod", name, "-n", namespace, "--ignore-not-found")
