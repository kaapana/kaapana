"""Cluster resource usage during a scenario, read from the platform's own
Prometheus via kaapana-backend's proxy — no cluster/SSH access needed, just
the same authenticated session everything else in this tool already uses.

node_* queries are cluster-wide (node-exporter, job "kubernetes-cadvisor"'s
sibling scrape); jobs_pod_* are the DAG task pods themselves (validator,
thumbnail, ...), which run in the "jobs" namespace, via cAdvisor.
"""

from __future__ import annotations

import math
import time

from client import KaapanaClient

QUERIES = {
    "node_cpu_pct": '100-(avg(rate(node_cpu_seconds_total{custom_job_name="node-exporter",mode="idle"}[1m]))*100)',
    "node_mem_used_bytes": (
        'sum(node_memory_MemTotal_bytes{custom_job_name="node-exporter"})'
        '-sum(node_memory_MemAvailable_bytes{custom_job_name="node-exporter"})'
    ),
    "node_disk_used_bytes": (
        'sum(node_filesystem_size_bytes{custom_job_name="node-exporter",fstype!="tmpfs"})'
        '-sum(node_filesystem_avail_bytes{custom_job_name="node-exporter",fstype!="tmpfs"})'
    ),
    "jobs_pod_cpu_cores": 'sum(rate(container_cpu_usage_seconds_total{namespace="jobs"}[1m]))',
    "jobs_pod_mem_bytes": 'sum(container_memory_working_set_bytes{namespace="jobs"})',
}


def usage_during(client: KaapanaClient, start_s: float) -> dict[str, dict[str, float]]:
    """{"avg": {name: value}, "max": {name: value}} for each query in
    QUERIES, over [start_s, now]. Best-effort per query and overall — a
    Prometheus hiccup must not fail the scenario, just omit the metric."""
    # +1: buffer for the query's own latency and Prometheus's scrape interval.
    minutes = max(1, math.ceil((time.time() - start_s) / 60) + 1)
    avg: dict[str, float] = {}
    peak: dict[str, float] = {}
    for name, query in QUERIES.items():
        try:
            points = [
                float(p["value"]) for p in client.query_range(query, minutes=minutes) if p.get("value") is not None
            ]
        except Exception:
            continue
        if points:
            avg[name] = sum(points) / len(points)
            peak[name] = max(points)
    return {"avg": avg, "max": peak}
