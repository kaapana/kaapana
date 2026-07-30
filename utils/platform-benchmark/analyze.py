#!/usr/bin/env python3
"""Analyze bottlenecks in a Kaapana ingestion DAG via the Airflow REST API.

  # send a DICOM file/dir and analyze exactly the run(s) it triggers
  python analyze.py --password admin --send /path/to/dicom/dir

  # or analyze the last N existing runs
  python analyze.py --password admin --limit 10
"""

from __future__ import annotations

import argparse
import json

from client import KaapanaClient
from core import analyze
from send import send_and_wait


def fmt(s: float) -> str:
    return f"{s*1000:.0f}ms" if s < 1 else f"{s:.1f}s"


def print_report(r: dict) -> None:
    if "error" in r:
        print(f"ERROR: {r['error']}")
        return
    print(f"DAG {r['dag_id']}: {r['runs']} runs ({r['failed']} failed)")
    print(f"  end-to-end p50 {fmt(r['dag_p50'])}, p95 {fmt(r['dag_p95'])}")
    print(f"  scheduler dead time per run (p50): {fmt(r['sched_gap_p50'])}")
    print()
    hdr = f"{'task':<38}{'runs':>5}{'p50':>9}{'p95':>9} | {'queue':>8}{'setup':>8}{'spawn':>8}{'code':>8}"
    print(hdr)
    print("─" * len(hdr))
    on_cp = set(r["critical_path"])
    order = sorted(r["tasks"], key=lambda t: -r["tasks"][t]["p50"])
    for tid in order:
        s = r["tasks"][tid]
        p = s["phases"]
        mark = "*" if tid in on_cp else " "
        print(
            f"{mark}{tid:<37}{s['count']:>5}{fmt(s['p50']):>9}{fmt(s['p95']):>9} |"
            f"{fmt(p['queue']):>8}{fmt(p['setup']):>8}{fmt(p['spawn']):>8}{fmt(p['code']):>8}"
        )
    if r["critical_path"]:
        cp_sum = sum(r["tasks"][t]["p50"] for t in r["critical_path"] if t in r["tasks"])
        print(f"\n* critical path ({fmt(cp_sum)} of task runtime): " + " → ".join(r["critical_path"]))
    print("\nphases (medians): queue=executor wait, setup=operator python before pod submit,")
    print("spawn=k8s schedule+image pull+container start, code=actual processing")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="https://e230-pc11.inet.dkfz-heidelberg.de")
    ap.add_argument("--username", default="kaapana")
    ap.add_argument("--password", required=True)
    ap.add_argument("--dag-id", default="service-process-incoming-dcm")
    ap.add_argument("--since", default=None, help="only runs started after this ISO timestamp")
    ap.add_argument("--limit", type=int, default=10, help="max runs to analyze (default 10)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--send", metavar="PATH", default=None,
                    help="dcmsend this DICOM file/dir and analyze exactly the triggered run(s)")
    ap.add_argument("--dataset", default="bottleneck-test", help="dataset name (dcmsend AE title)")
    ap.add_argument("--project", default="admin", help="target project (dcmsend called AET kp-<project>)")
    ap.add_argument("--reset", action="store_true",
                    help="delete the series (delete-series DAG) before sending, for a clean ingest")
    args = ap.parse_args()

    client = KaapanaClient(args.host, args.username, args.password)
    if args.send:
        runs, _ = send_and_wait(client, args.dag_id, args.send, args.dataset, args.project, reset=args.reset)
        result = analyze(client, args.dag_id, runs=runs)
    else:
        result = analyze(client, args.dag_id, args.since, args.limit)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)


if __name__ == "__main__":
    main()
