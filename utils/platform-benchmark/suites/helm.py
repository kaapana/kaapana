"""Helm-deploy suite: time install/uninstall of a synthetic chart at increasing
sizes, to catch machines where big charts run into the helm timeout.

Size N submits 3N objects (ConfigMap + Deployment + Service each). The chart is
a local temp dir, so the helm entrypoint must reach the cluster from here.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from suites.k8s import sh

RELEASE = "benchmark-helm"

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
  replicas: {{ int $.Values.replicas }}
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


def write_chart(dir: Path) -> None:
    (dir / "Chart.yaml").write_text(CHART_YAML)
    (dir / "values.yaml").write_text(f"count: 1\nreplicas: 0\npayload: {'x' * 4096}\n")
    (dir / "templates").mkdir()
    (dir / "templates" / "bench.yaml").write_text(TEMPLATE)


def run(
    helm: str = "helm",
    kubectl: str = "kubectl",
    namespace: str = "benchmark-helm",
    sizes: tuple[int, ...] = (10, 50, 100),
    replicas: int = 0,
    timeout_s: int = 3600,
) -> dict:
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        chart = Path(tmp) / "chart"
        chart.mkdir()
        write_chart(chart)
        try:
            for n in sizes:
                print(f"=== size x{n}: {3 * n} objects ===")
                # a timeout at one size must not discard the smaller sizes
                try:
                    try:
                        t0 = time.time()
                        sh(
                            helm,
                            "install",
                            RELEASE,
                            str(chart),
                            "-n",
                            namespace,
                            "--create-namespace",
                            "--wait",
                            f"--timeout={timeout_s}s",
                            "--set",
                            f"count={n}",
                            "--set",
                            f"replicas={replicas}",
                        )
                        install_s = time.time() - t0
                        t0 = time.time()
                        sh(helm, "uninstall", RELEASE, "-n", namespace, "--wait", f"--timeout={timeout_s}s")
                        uninstall_s = time.time() - t0
                    finally:
                        try:  # never leave the release behind
                            sh(helm, "uninstall", RELEASE, "-n", namespace, "--ignore-not-found")
                        except RuntimeError:
                            pass
                except Exception as e:
                    results[f"x{n}"] = {"objects": 3 * n, "error": str(e)}
                    print(f"    FAILED: {e}")
                    break
                results[f"x{n}"] = {
                    "objects": 3 * n,
                    "install_s": round(install_s, 1),
                    "uninstall_s": round(uninstall_s, 1),
                }
                print(f"    install {install_s:.1f}s, uninstall {uninstall_s:.1f}s")
        finally:
            sh(kubectl, "delete", "namespace", namespace, "--ignore-not-found", "--wait=false")
    return results
