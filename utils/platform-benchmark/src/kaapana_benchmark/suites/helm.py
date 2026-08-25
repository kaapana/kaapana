"""Helm suite: how long the cluster takes to install charts of growing size.

Each size unit is one ConfigMap (~4 KB), one Deployment and one Service, so
size N pushes 3N objects through the API server and etcd. Replicas are 0: this
measures chart handling, not pod scheduling.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from .. import kubectl
from ..model import NO_DIRECTION, Metric, Sample

NAME = "helm"
RELEASE = "benchmark-helm"
NAMESPACE = "benchmark-helm"
SIZES = (10, 50, 100)
TIMEOUT_S = 600

METRICS = {
    "install_seconds": Metric("helm_install_seconds", "seconds"),
    "uninstall_seconds": Metric("helm_uninstall_seconds", "seconds"),
    "failed": Metric("helm_failed", "", NO_DIRECTION, invalidates_case=True),
}

CHART_YAML = """\
apiVersion: v2
name: benchmark-helm
description: synthetic chart for deploy-speed benchmarking
version: 0.1.0
"""

TEMPLATE = """\
{{- range $i := until (int $.Values.count) }}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: bench-cm-{{ $i }}
data:
  payload: {{ $.Values.payload | quote }}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bench-dep-{{ $i }}
spec:
  replicas: 0
  selector:
    matchLabels:
      app: bench-{{ $i }}
  template:
    metadata:
      labels:
        app: bench-{{ $i }}
    spec:
      containers:
        - name: pause
          image: registry.k8s.io/pause:3.9
---
apiVersion: v1
kind: Service
metadata:
  name: bench-svc-{{ $i }}
spec:
  selector:
    app: bench-{{ $i }}
  ports:
    - port: 80
{{- end }}
"""


def helm_command(kubectl_prefix: str) -> str:
    """"ssh host microk8s kubectl" -> "ssh host microk8s helm"."""
    words = kubectl_prefix.split()
    return " ".join(words[:-1] + ["helm"]) if words else "helm"


def write_chart(directory: Path) -> None:
    (directory / "Chart.yaml").write_text(CHART_YAML)
    (directory / "values.yaml").write_text(f"count: 1\npayload: {'x' * 4096}\n")
    (directory / "templates").mkdir()
    (directory / "templates" / "bench.yaml").write_text(TEMPLATE)


def install_and_remove(helm: str, chart: Path, size: int) -> tuple[float, float]:
    started = time.monotonic()
    kubectl.run(helm, "install", RELEASE, str(chart), "-n", NAMESPACE,
                "--create-namespace", "--wait", f"--timeout={TIMEOUT_S}s",
                "--set", f"count={size}")
    install_s = time.monotonic() - started

    started = time.monotonic()
    kubectl.run(helm, "uninstall", RELEASE, "-n", NAMESPACE, "--wait", f"--timeout={TIMEOUT_S}s")
    return install_s, time.monotonic() - started


def run(target) -> list[Sample]:
    helm = helm_command(target.kubectl)
    samples: list[Sample] = []
    with tempfile.TemporaryDirectory() as workspace:
        chart = Path(workspace) / "chart"
        chart.mkdir()
        write_chart(chart)
        try:
            for size in SIZES:
                case = f"x{size}"
                print(f"=== helm {case}: {3 * size} objects ===")
                try:
                    install_s, uninstall_s = install_and_remove(helm, chart, size)
                except Exception as error:
                    print(f"  ! failed: {error}")
                    samples.append(Sample(case, METRICS["failed"], 1))
                    break
                samples += [
                    Sample(case, METRICS["install_seconds"], round(install_s, 1)),
                    Sample(case, METRICS["uninstall_seconds"], round(uninstall_s, 1)),
                    Sample(case, METRICS["failed"], 0),
                ]
                print(f"  install {install_s:.1f}s, uninstall {uninstall_s:.1f}s")
        finally:
            kubectl.run(helm, "uninstall", RELEASE, "-n", NAMESPACE, "--ignore-not-found")
            kubectl.run(target.kubectl, "delete", "namespace", NAMESPACE,
                        "--ignore-not-found", "--wait=false")
    return samples
