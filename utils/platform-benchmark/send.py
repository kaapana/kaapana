"""Send DICOMs with dcmsend and wait for the ingestion runs they trigger.

The DICOM receiver batches incoming instances per series and triggers one
``service-process-incoming-dcm`` run per series, with the SeriesInstanceUID in
the run conf — that is how a send is correlated with its exact run(s).
"""

from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone
from multiprocessing.pool import ThreadPool
from pathlib import Path

from client import KaapanaClient


def series_uids(paths: str | list[str]) -> set[str]:
    """Unique SeriesInstanceUIDs of all DICOM files under *paths* (via dcmdump)."""
    files = []
    for path in [paths] if isinstance(paths, str) else paths:
        p = Path(path)
        files += [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file()]
    out = subprocess.run(
        ["dcmdump", *map(str, files)], capture_output=True, text=True,
    ).stdout
    # only top-level SeriesInstanceUID (line starts at column 0); dcmdump indents
    # elements nested in sequences — e.g. a SEG/RTSTRUCT references its source
    # series' UID inside a sequence, which is not a series that gets ingested.
    # (+P would print nested matches un-indented, so it is deliberately not used.)
    uids = {
        line.split("[")[1].split("]")[0]
        for line in out.splitlines()
        if line.startswith("(0020,000e)") and "[" in line
    }
    if not uids:
        raise RuntimeError(f"no DICOM files with a SeriesInstanceUID found under {paths}")
    return uids


def dcmsend(host: str, paths: str | list[str], dataset: str, project: str) -> None:
    cmd = [
        "dcmsend", host, "11112", "--scan-directories", "--recurse",
        "--aetitle", dataset, "--call", f"kp-{project}",
        *([paths] if isinstance(paths, str) else paths),
    ]
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def dcmsend_trickle(host: str, paths: list[str], dataset: str, project: str,
                    chunk_size: int, pause_s: float) -> None:
    """Simulate slow senders: every series is its own association stream that
    sends *chunk_size* instances, pauses *pause_s* seconds, sends the next
    chunk, ... — all series concurrently. This exercises the receiver's
    settle-timer (unchangedCounter): with a pause below the quiescence window
    each series must still end up in exactly one DAG run, not be split."""
    def send_series(series_dir: str) -> None:
        files = sorted(str(f) for f in Path(series_dir).rglob("*") if f.is_file())
        for i in range(0, len(files), chunk_size):
            if i:
                time.sleep(pause_s)
            subprocess.run(
                ["dcmsend", host, "11112", "--aetitle", dataset,
                 "--call", f"kp-{project}", *files[i:i + chunk_size]],
                check=True, stdout=subprocess.DEVNULL,
            )

    print(f"$ dcmsend (trickle: {chunk_size} instances per chunk, "
          f"{pause_s}s pause, {len(paths)} series in parallel)")
    with ThreadPool(len(paths)) as pool:
        pool.map(send_series, paths)


def wait_for_runs(
    client: KaapanaClient, dag_id: str, uids: set[str], since: str,
    timeout: int = 1800, dropped_grace: int = 300,
) -> list[dict]:
    """Poll until one finished run per sent series shows up; return those runs.

    The platform can silently drop a series under load (positive C-STORE but no
    DAG run — the known ingest bug). If every triggered run has finished but the
    run count stays short of the sent series for *dropped_grace* seconds, return
    what we have instead of timing out; the caller reports the missing runs."""
    deadline = time.time() + timeout
    print(f"waiting for {len(uids)} run(s) (receiver batches ~60s before triggering) ...")
    all_done_since, last_count, confirm = None, 0, 0
    while time.time() < deadline:
        runs = [
            r for r in client.get_dag_runs(dag_id, since, 100)
            if r.get("conf", {}).get("seriesInstanceUID") in uids
        ]
        states = [r["state"] for r in runs]
        print(f"  {len(runs)}/{len(uids)} triggered, states: {states or '—'}")
        finished = bool(runs) and all(s in ("success", "failed") for s in states)
        if len(runs) != last_count or not finished:
            all_done_since, confirm = None, 0
        last_count = len(runs)
        if finished:
            if len(runs) >= len(uids):
                # one confirmation poll: a split series can trigger a late
                # extra run after the count already looks complete
                if confirm >= 1:
                    return runs
                confirm += 1
                time.sleep(15)
                continue
            all_done_since = all_done_since or time.time()
            if time.time() - all_done_since > dropped_grace:
                print(f"  ⚠ {len(uids) - len(runs)} series never triggered a run "
                      f"(silently dropped by the receiver?) — continuing with {len(runs)}")
                return runs
        time.sleep(15)
    raise TimeoutError(f"runs did not finish within {timeout}s")


def delete_and_wait(client: KaapanaClient, uids: set[str], timeout: int = 600) -> None:
    """Run the delete-series DAG on the given series and wait for it to finish, so a
    rerun ingests from a clean state instead of re-processing existing series."""
    since = datetime.now(timezone.utc).isoformat()
    print(f"deleting {len(uids)} series (delete-series) before upload ...")
    client.trigger_workflow(
        "delete-series", sorted(uids),
        {"single_execution": False, "delete_complete_study": False},
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        runs = [r for r in client.get_dag_runs("delete-series", since, 10)]
        if runs and all(r["state"] in ("success", "failed") for r in runs):
            print(f"  delete-series done: {[r['state'] for r in runs]}")
            return
        time.sleep(10)
    raise TimeoutError("delete-series did not finish in time")


def send_and_wait(
    client: KaapanaClient, dag_id: str, paths: str | list[str], dataset: str,
    project: str, reset: bool = True, timeout: int = 1800,
    trickle: tuple[int, float] | None = None,
) -> tuple[list[dict], set[str]]:
    """Returns (runs, sent series UIDs) — the UIDs are the denominator for
    dropped-series accounting (a patient dir may hold more than one series).

    With ``trickle=(chunk_size, pause_s)`` the series are sent in small chunks
    with pauses instead of one bulk dcmsend (see dcmsend_trickle)."""
    uids = series_uids(paths)
    if reset:
        delete_and_wait(client, uids)
    print(f"sending {len(uids)} series")
    since = datetime.now(timezone.utc).isoformat()
    host = client.host.split("//")[-1]
    if trickle:
        dcmsend_trickle(host, [paths] if isinstance(paths, str) else paths,
                        dataset, project, *trickle)
    else:
        dcmsend(host, paths, dataset, project)
    return wait_for_runs(client, dag_id, uids, since, timeout), uids
