"""Helm-deploy suite: time `helm install --wait` / `helm uninstall --wait` of a
synthetic chart at increasing sizes, to catch machines where big charts (like
kaapana-platform-chart) run into the helm timeout.

Each size unit is 1 ConfigMap (~4 KB payload) + 1 Deployment + 1 Service, so
size N submits 3N objects through the API server / etcd. Deployments default to
0 replicas — the suite measures chart handling, not pod scheduling; pass
replicas=1 to also schedule pause pods. Everything runs in its own namespace,
which is deleted afterwards no matter what.

helm/kubectl must run where this suite runs (the generated chart is a local
directory) — for a remote instance, point KUBECONFIG at it or run the tool there.
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
    (dir / "values.yaml").write_text(
        f"count: 1\nreplicas: 0\npayload: {'x' * 4096}\n")
    (dir / "templates").mkdir()
    (dir / "templates" / "bench.yaml").write_text(TEMPLATE)


def run(helm: str, kubectl: str, namespace: str, sizes: list[int],
        replicas: int = 0, timeout_s: int = 600) -> dict:
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        chart = Path(tmp) / "chart"
        chart.mkdir()
        write_chart(chart)
        try:
            for n in sizes:
                print(f"=== size x{n}: {3 * n} objects ===")
                # a timeout at one size (the failure this suite exists to
                # catch) must not throw away the completed smaller sizes
                try:
                    try:
                        t0 = time.time()
                        sh(helm, "install", RELEASE, str(chart), "-n", namespace,
                           "--create-namespace", "--wait", f"--timeout={timeout_s}s",
                           "--set", f"count={n}", "--set", f"replicas={replicas}")
                        install_s = time.time() - t0
                        t0 = time.time()
                        sh(helm, "uninstall", RELEASE, "-n", namespace, "--wait",
                           f"--timeout={timeout_s}s")
                        uninstall_s = time.time() - t0
                    finally:
                        try:  # never leave the release behind, even on error/timeout
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
