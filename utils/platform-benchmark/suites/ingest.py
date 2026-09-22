"""Ingestion suite: dcmsend the directories of each scenario and measure the DAG
runs they trigger (see core.py for the phase breakdown)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import resources
from client import KaapanaClient
from core import _ts, analyze
from send import dir_stats, send_and_wait


def load(path: Path) -> tuple[str, dict[str, list[str]]]:
    """{root_path: "...", scenarios: {name: [directory, ...]}} — root_path is
    the subdirectory of --data-dir the directories are relative to (omit or
    leave "" to use --data-dir itself). Directories are any mix of modality
    and patient directories, sent recursively."""
    doc = json.loads(Path(path).read_text())
    return doc.get("root_path", ""), doc["scenarios"]


def scenario_paths(data_dir: Path, root_path: str, entries: list[str]) -> list[str]:
    base = data_dir / root_path if root_path else data_dir
    paths = []
    for entry in entries:
        path = base / entry
        if not path.is_dir():
            raise RuntimeError(f"scenario directory not found: {path}")
        paths.append(str(path))
    return paths


def peak_active_runs(runs: list[dict]) -> int:
    """Maximum number of runs running at once; equals max_active_runs when
    more series than the cap are sent."""
    events = []
    for r in runs:
        s, e = _ts(r.get("start_date")), _ts(r.get("end_date"))
        if s and e:
            events += [(s, 1), (e, -1)]
    peak = cur = 0
    for _, delta in sorted(events):
        cur += delta
        peak = max(peak, cur)
    return peak


def run(
    host: str,
    username: str,
    password: str,
    dag_id: str,
    data_dir: Path,
    root_path: str,
    config: dict[str, list[str]],
    names: list[str],
    reset: bool = True,
    timeout_s: int = 4 * 3600,
) -> dict:
    client = KaapanaClient(host, username, password)
    results = {}
    for name in names:
        paths = scenario_paths(Path(data_dir), root_path, config[name])
        num_files, disk_size_bytes = dir_stats(paths)
        sent = {"files": num_files, "disk_size_bytes": disk_size_bytes}
        print(
            f"\n=== scenario {name}: {', '.join(config[name])} ({num_files} files, {disk_size_bytes / 1e6:.0f} MB) ==="
        )
        t0 = time.time()
        try:
            dag_runs, uids = send_and_wait(
                client,
                dag_id,
                paths,
                dataset=f"bench-{name}",
                project="admin",
                reset=reset,
                timeout=timeout_s,
            )
        except Exception as e:  # keep the other scenarios' results
            print(f"    x scenario failed: {e}")
            results[name] = {**sent, "failed_scenario": 1, "error": str(e)}
            continue
        wall = time.time() - t0
        r = analyze(client, dag_id, runs=dag_runs)
        usage = resources.usage_during(client, t0)
        triggered = {d.get("conf", {}).get("seriesInstanceUID") for d in dag_runs}
        tasks = r["tasks"]
        results[name] = {
            **sent,
            "series": len(uids),
            "failed_scenario": 0,
            "wall_s": round(wall, 1),
            "run_p50_s": round(r["dag_p50"], 1),
            "run_p95_s": round(r["dag_p95"], 1),
            "sched_gap_p50_s": round(r["sched_gap_p50"], 1),
            "peak_active_runs": peak_active_runs(dag_runs),
            "failed_runs": r["failed"],
            "dropped_series": len(uids - triggered),
            # >0 = a series was cut into several runs (settle timer fired early)
            "split_runs": len(dag_runs) - len(triggered),
            # per task_id, for every task in the DAG (not just the slowest) so a
            # dashboard can pick what to show
            "task_count": {t: s["count"] for t, s in tasks.items()},
            "task_p50_s": {t: round(s["p50"], 1) for t, s in tasks.items()},
            "task_p95_s": {t: round(s["p95"], 1) for t, s in tasks.items()},
            "task_avg_s": {t: round(s["avg"], 1) for t, s in tasks.items()},
            "task_phase_queue_s": {t: round(s["phases"]["queue"], 1) for t, s in tasks.items()},
            "task_phase_setup_s": {t: round(s["phases"]["setup"], 1) for t, s in tasks.items()},
            "task_phase_spawn_s": {t: round(s["phases"]["spawn"], 1) for t, s in tasks.items()},
            "task_phase_code_s": {t: round(s["phases"]["code"], 1) for t, s in tasks.items()},
            "critical_path": r["critical_path"],
            "resource_avg": usage["avg"],
            "resource_max": usage["max"],
        }
        print(
            f"    wall {wall:.0f}s, run p50 {r['dag_p50']:.0f}s, "
            f"peak active runs {results[name]['peak_active_runs']}, failed {r['failed']}, "
            f"dropped {results[name]['dropped_series']}"
        )
    return results
