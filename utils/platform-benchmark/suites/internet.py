"""Internet suite: run the existing speedtest image (utils/internet-benchmark)
as a pod on the instance's cluster and parse its --json output."""

from __future__ import annotations

import json

from suites.k8s import run_pod

POD_NAME = "benchmark-speedtest"
IMAGE = "klakadkfz/speedtest"
NO_PROXY = "localhost,127.0.0.1,169.254.169.254,dkfz-heidelberg.de,10.1.0.0/16,10.152.183.0/24"


def manifest(namespace: str, proxy: str | None) -> str:
    env = []
    if proxy:
        env = [
            {"name": "https_proxy", "value": proxy},
            {"name": "http_proxy", "value": proxy},
            {"name": "no_proxy", "value": NO_PROXY},
        ]
    return json.dumps({
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": POD_NAME, "namespace": namespace},
        "spec": {
            "restartPolicy": "Never",
            "containers": [{
                "name": "speedtest",
                "image": IMAGE,
                "imagePullPolicy": "IfNotPresent",
                "command": ["python3", "-u", "/speedtest.py", "--json"],
                "env": env,
            }],
        },
    })


def run(kubectl: str, namespace: str, proxy: str | None, timeout_s: int = 300) -> dict:
    logs = run_pod(kubectl, manifest(namespace, proxy), POD_NAME, namespace, timeout_s)
    line = next(l for l in reversed(logs.splitlines()) if l.startswith("{"))
    r = json.loads(line)
    return {
        "ping_ms": round(r["ping"], 1),
        "download_mbps": round(r["download"] / 1e6, 1),
        "upload_mbps": round(r["upload"] / 1e6, 1),
        "server": r.get("server", {}).get("sponsor", ""),
    }
