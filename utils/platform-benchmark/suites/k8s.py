"""Run a pod to completion on the instance's cluster and return its logs."""

from __future__ import annotations

import shlex
import subprocess
import time


def sh(prefix: str, *argv: str, stdin: str | None = None) -> str:
    """Run a command built from a configurable prefix ("kubectl", "ssh host helm")."""
    proc = subprocess.run(
        shlex.split(prefix) + list(argv),
        input=stdin,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{prefix} {' '.join(argv)} failed: {proc.stderr.strip()}")
    return proc.stdout


def run_pod(kubectl: str, manifest: str, name: str, namespace: str, timeout_s: int) -> str:
    """Apply a pod manifest, wait until it finishes, return its logs, delete it."""
    sh(kubectl, "delete", "pod", name, "-n", namespace, "--ignore-not-found", "--wait=true")
    sh(kubectl, "apply", "-n", namespace, "-f", "-", stdin=manifest)
    try:
        deadline = time.time() + timeout_s
        while True:
            phase = sh(kubectl, "get", "pod", name, "-n", namespace, "-o", "jsonpath={.status.phase}").strip()
            if phase in ("Succeeded", "Failed"):
                break
            if time.time() > deadline:
                raise TimeoutError(f"pod {name} still in phase {phase!r} after {timeout_s}s")
            time.sleep(5)
        logs = sh(kubectl, "logs", name, "-n", namespace)
        if phase == "Failed":
            raise RuntimeError(f"pod {name} failed:\n{logs[-2000:]}")
        return logs
    finally:
        sh(kubectl, "delete", "pod", name, "-n", namespace, "--ignore-not-found")
