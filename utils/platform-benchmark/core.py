"""Per-task phase breakdown (queue / setup / pod spawn / code) + critical path."""

from __future__ import annotations

import math
import re
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from client import KaapanaClient

# Airflow log line prefix, e.g. "[2026-07-13T10:00:00.123+0000] {...} INFO - ..."
# Captures the offset ("+0000", "+00:00", "Z") so log times can be compared
# with the (timezone-aware) Airflow API timestamps.
LOG_TS = re.compile(r"^\[(\d{4}-\d{2}-\d{2}[T ][\d:.]+)(Z|[+-]\d{2}:?\d{2})?\]", re.M)
POD_CREATE = "Creating pod '"


def _ts(iso: str | None) -> datetime | None:
    if not iso:
        return None
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _parse_log_ts(raw: str, offset: str | None) -> datetime:
    dt = datetime.fromisoformat(raw.replace(" ", "T"))
    if not offset or offset == "Z":
        tz = timezone.utc  # Airflow logs default to UTC
    else:
        off = offset.replace(":", "")
        sign = 1 if off[0] == "+" else -1
        tz = timezone(sign * timedelta(hours=int(off[1:3]), minutes=int(off[3:5])))
    return dt.replace(tzinfo=tz)


def split_phases(client: KaapanaClient, dag_id: str, run_id: str, ti: dict) -> dict:
    """Break one task instance into phases (seconds):

    queue  : queued_when -> start_date        (executor slot / worker pickup)
    setup  : start_date -> 'Creating pod'     (operator python before pod submit)
    spawn  : 'Creating pod' -> next log line  (k8s scheduling, image pull, container start)
    code   : first container output -> end_date

    Tasks that never log a pod creation (local operators) get their whole
    runtime attributed to 'code'.
    """
    queued = _ts(ti.get("queued_when"))
    start = _ts(ti.get("start_date"))
    end = _ts(ti.get("end_date"))
    phases = {"queue": 0.0, "setup": 0.0, "spawn": 0.0, "code": 0.0}
    if not (start and end):
        return phases
    if queued:
        phases["queue"] = max(0.0, (start - queued).total_seconds())

    t_create = t_running = None
    try:
        log = client.get_task_log(dag_id, run_id, ti["task_id"], ti.get("try_number") or 1)
        lines = log.splitlines()
        for i, line in enumerate(lines):
            if POD_CREATE in line:
                m = LOG_TS.match(line)
                if m:
                    t_create = _parse_log_ts(m.group(1), m.group(2))
                # first timestamped line after pod creation that is not a
                # pending-phase poll is the start of streamed container output
                for later in lines[i + 1:]:
                    if "Pod in phase" in later:
                        continue
                    m2 = LOG_TS.match(later)
                    if m2:
                        t_running = _parse_log_ts(m2.group(1), m2.group(2))
                        break
                break
    except Exception:
        pass

    if t_create and t_running:
        phases["setup"] = max(0.0, (t_create - start).total_seconds())
        phases["spawn"] = max(0.0, (t_running - t_create).total_seconds())
        phases["code"] = max(0.0, (end - t_running).total_seconds())
    else:
        phases["code"] = max(0.0, (end - start).total_seconds())
    return phases


def critical_path(tasks: list[dict], weights: dict[str, float]) -> list[str]:
    """Maximum-weight root->leaf path through the DAG (DP over downstream edges)."""
    downstream = {t["task_id"]: t.get("downstream_task_ids", []) for t in tasks}
    upstream_of = {tid for ds in downstream.values() for tid in ds}
    roots = [tid for tid in downstream if tid not in upstream_of]
    memo: dict[str, float] = {}

    def longest(tid: str) -> float:
        if tid not in memo:
            best = max((longest(d) for d in downstream[tid]), default=0.0)
            memo[tid] = weights.get(tid, 0.0) + best
        return memo[tid]

    if not roots:
        return []
    path = [max(roots, key=longest)]
    while downstream[path[-1]]:
        path.append(max(downstream[path[-1]], key=lambda d: memo.get(d, longest(d))))
    return path


def pct(values: list[float], p: float) -> float:
    """Nearest-rank percentile: s[ceil(p*n) - 1]."""
    if not values:
        return 0.0
    s = sorted(values)
    return s[max(0, math.ceil(p * len(s)) - 1)]


def analyze(
    client: KaapanaClient,
    dag_id: str,
    since: str | None = None,
    limit: int = 10,
    runs: list[dict] | None = None,
) -> dict:
    if runs is None:
        runs = client.get_dag_runs(dag_id, since, limit)
    runs = [r for r in runs if r.get("state") in ("success", "failed")]
    if not runs:
        return {"error": f"no finished runs of '{dag_id}' found"}

    task_phases: dict[str, list[dict]] = defaultdict(list)
    dag_durations, sched_gaps = [], []
    for run in runs:
        tis = client.get_task_instances(dag_id, run["dag_run_id"])
        done = {}
        for ti in tis:
            if ti.get("start_date") and ti.get("end_date"):
                task_phases[ti["task_id"]].append(
                    split_phases(client, dag_id, run["dag_run_id"], ti)
                )
                done[ti["task_id"]] = ti
        s, e = _ts(run.get("start_date")), _ts(run.get("end_date"))
        if s and e:
            dag_durations.append((e - s).total_seconds())
            # dead time the scheduler adds between/around tasks: run duration
            # minus the union of the intervals covered by task instances
            # (parallel tasks overlap and must not be double-counted; note the
            # gap still includes executor queue time of the tasks themselves)
            intervals = sorted(
                (_ts(t["start_date"]), _ts(t["end_date"])) for t in done.values()
            )
            busy = 0.0
            cur_start = cur_end = None
            for i_start, i_end in intervals:
                if cur_end is None or i_start > cur_end:
                    if cur_end is not None:
                        busy += (cur_end - cur_start).total_seconds()
                    cur_start, cur_end = i_start, i_end
                else:
                    cur_end = max(cur_end, i_end)
            if cur_end is not None:
                busy += (cur_end - cur_start).total_seconds()
            sched_gaps.append(max(0.0, dag_durations[-1] - busy))

    stats = {}
    for tid, plist in task_phases.items():
        total = [sum(p.values()) - p["queue"] for p in plist]  # queue not part of runtime
        stats[tid] = {
            "count": len(plist),
            "p50": pct(total, 0.5),
            "p95": pct(total, 0.95),
            "avg": statistics.mean(total),
            "phases": {k: pct([p[k] for p in plist], 0.5) for k in ("queue", "setup", "spawn", "code")},
        }

    try:
        cpath = critical_path(client.get_dag_tasks(dag_id), {t: s["p50"] for t, s in stats.items()})
    except Exception:
        cpath = []

    return {
        "dag_id": dag_id,
        "runs": len(runs),
        "failed": sum(1 for r in runs if r["state"] == "failed"),
        "dag_p50": pct(dag_durations, 0.5),
        "dag_p95": pct(dag_durations, 0.95),
        "sched_gap_p50": pct(sched_gaps, 0.5),
        "tasks": stats,
        "critical_path": cpath,
    }
