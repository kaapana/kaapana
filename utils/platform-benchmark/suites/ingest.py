"""Ingestion-pipeline suite: send a fixed DICOM scenario set through the
platform's public APIs and measure where time goes (see analyze.py/core.py).

Four modes (each scenario deletes its series first, then sends and waits):
  single   1 series of each modality, sequentially (per-run baseline)
  medium   mixed-x15: 5 CT + 5 SEG + 5 SM concurrently (below the run cap)
  max      max-x40: 10 CT + 10 SEG + 10 RTSTRUCT + 10 SM concurrently — twice
           the DAG's max_active_runs=20, so runs must queue; peak_active_runs
           verifies the cap is actually reached
  trickle  trickle-x5: 5 CT series sent concurrently, but each in chunks of
           10 instances with a 5s pause between chunks (a slow sender).
           The pause is below the receiver's quiescence window, so every
           series must still land in exactly one run — split_runs / dropped
           series expose receivers that cut a series apart mid-transfer
"""

from __future__ import annotations

import time
from pathlib import Path

from client import KaapanaClient
from core import _ts, analyze
from send import send_and_wait

# modality -> subpath under the data dir; each leaf <patient> dir is one series
CT_DIR = "NSCLC/CT"
SEG_DIR = "NSCLC/SEG"
RTSTRUCT_DIR = "NSCLC/RTSTRUCT"
SM_DIR = "CDDP-EAGLE/SM"

MODES = ("single", "medium", "max", "trickle")

# trickle mode: instances per chunk / pause between chunks per series
TRICKLE_CHUNK_SIZE = 10
TRICKLE_PAUSE_S = 5.0
TRICKLE_SERIES = 5


def discover_data(data_dir: Path) -> dict[str, list[str]]:
    """Enumerate one series per <patient> folder from the standard image_modalities
    layout (NSCLC/{CT,SEG,RTSTRUCT}/<patient>, CDDP-EAGLE/SM/<patient>). CT, SEG and
    RTSTRUCT are paired by patient folder name, so index i is the same patient."""
    def patients(sub: str) -> dict[str, str]:
        root = data_dir / sub
        return {d.name: str(d) for d in sorted(root.iterdir()) if d.is_dir()} if root.is_dir() else {}

    ct, seg, rt, sm = patients(CT_DIR), patients(SEG_DIR), patients(RTSTRUCT_DIR), patients(SM_DIR)
    shared = sorted(ct.keys() & seg.keys() & rt.keys())
    return {
        "CT": [ct[p] for p in shared],
        "SEG": [seg[p] for p in shared],
        "RTSTRUCT": [rt[p] for p in shared],
        "SM": sorted(sm.values()),
    }


def scenarios(data: dict[str, list[str]], mode: str) -> list[tuple[str, list[str]]]:
    """Scenario name -> series dirs for one mode; raises if the data dir is too small."""
    need = {"single": 1, "medium": 5, "max": 10, "trickle": TRICKLE_SERIES}[mode]
    short = {m: len(v) for m, v in data.items() if len(v) < need}
    if short:
        raise RuntimeError(
            f"mode {mode!r} needs {need} series per modality, found only {short} "
            f"(expected {CT_DIR}, {SEG_DIR}, {RTSTRUCT_DIR}, {SM_DIR})"
        )
    if mode == "single":
        return [(f"{m.lower()}-single", [data[m][0]]) for m in ("CT", "SEG", "RTSTRUCT", "SM")]
    if mode == "medium":
        return [("mixed-x15", data["CT"][:5] + data["SEG"][:5] + data["SM"][:5])]
    if mode == "trickle":
        return [(f"trickle-x{TRICKLE_SERIES}", data["CT"][:TRICKLE_SERIES])]
    return [("max-x40", data["CT"][:10] + data["SEG"][:10] + data["RTSTRUCT"][:10] + data["SM"][:10])]


def peak_active_runs(runs: list[dict]) -> int:
    """Maximum number of DAG runs in the 'running' state at once (sweep line over
    run start/end); with more series than max_active_runs this should equal the cap."""
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


def run(host: str, username: str, password: str, dag_id: str,
        data_dir: Path, mode: str = "all", reset: bool = True) -> dict:
    data = discover_data(data_dir)
    print("data: " + ", ".join(f"{len(v)} {m}" for m, v in data.items()))
    client = KaapanaClient(host, username, password)
    modes = MODES if mode == "all" else (mode,)
    results = {}
    for m in modes:
        for name, paths in scenarios(data, m):
            print(f"\n=== mode {m} — scenario {name} ({len(paths)} series) ===")
            t0 = time.time()
            try:
                runs, uids = send_and_wait(
                    client, dag_id, paths, dataset=f"bench-{name}", project="admin",
                    reset=reset, timeout=3600 if m == "max" else 1800,
                    trickle=(TRICKLE_CHUNK_SIZE, TRICKLE_PAUSE_S) if m == "trickle" else None,
                )
            except Exception as e:  # keep the other scenarios' results
                print(f"    ✗ scenario failed: {e}")
                results[name] = {"series": len(paths), "error": str(e)}
                continue
            wall = time.time() - t0
            r = analyze(client, dag_id, runs=runs)
            peak = peak_active_runs(runs)
            triggered = {r.get("conf", {}).get("seriesInstanceUID") for r in runs}
            results[name] = {
                "series": len(uids),
                "wall_s": round(wall, 1),
                "run_p50_s": round(r["dag_p50"], 1),
                "run_p95_s": round(r["dag_p95"], 1),
                "sched_gap_p50_s": round(r["sched_gap_p50"], 1),
                "peak_active_runs": peak,
                "failed_runs": r["failed"],
                "dropped_series": len(uids - triggered),
                # >0 means a series was cut into several runs (settle-timer
                # fired mid-transfer) — the trickle scenario's main signal
                "split_runs": len(runs) - len(triggered),
                "slowest_tasks": {
                    t: round(s["p50"], 1)
                    for t, s in sorted(r["tasks"].items(), key=lambda kv: -kv[1]["p50"])[:3]
                },
            }
            print(f"    wall {wall:.0f}s, run p50 {r['dag_p50']:.0f}s, "
                  f"peak active runs {peak}, failed {r['failed']}, "
                  f"dropped {results[name]['dropped_series']}")
    return results
