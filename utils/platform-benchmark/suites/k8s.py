"""Run a pod to completion on the instance's cluster and return its logs.

The kubectl entrypoint is a configurable command string, e.g. "kubectl",
"microk8s kubectl" or "ssh e230-pc11 microk8s kubectl" — the suites only
need apply/get/logs/delete.
"""

from __future__ import annotations

import shlex
import subprocess
import time


def sh(prefix: str, *argv: str, stdin: str | None = None) -> str:
    """Run a command built from a configurable prefix ("kubectl", "ssh host helm", ...)."""
    proc = subprocess.run(
        shlex.split(prefix) + list(argv),
        input=stdin, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{prefix} {' '.join(argv)} failed: {proc.stderr.strip()}")
    return proc.stdout


_kubectl = sh


def run_pod(kubectl: str, manifest: str, name: str, namespace: str, timeout_s: int) -> str:
    """Apply a pod manifest, wait until it finishes, return its logs, delete it."""
    _kubectl(kubectl, "delete", "pod", name, "-n", namespace, "--ignore-not-found", "--wait=true")
    _kubectl(kubectl, "apply", "-n", namespace, "-f", "-", stdin=manifest)
    try:
        deadline = time.time() + timeout_s
        while True:
            phase = _kubectl(kubectl, "get", "pod", name, "-n", namespace,
                             "-o", "jsonpath={.status.phase}").strip()
            if phase in ("Succeeded", "Failed"):
                break
            if time.time() > deadline:
                raise TimeoutError(f"pod {name} still in phase {phase!r} after {timeout_s}s")
            time.sleep(5)
        logs = _kubectl(kubectl, "logs", name, "-n", namespace)
        if phase == "Failed":
            raise RuntimeError(f"pod {name} failed:\n{logs[-2000:]}")
        return logs
    finally:
        _kubectl(kubectl, "delete", "pod", name, "-n", namespace, "--ignore-not-found")
