"""Ingestion-pipeline suite.

Sends DICOM series to the platform receiver and measures the
service-process-incoming-dcm runs they trigger. A scenario file names the
dataset paths each scenario sends.

Scenarios above the DAG's max_active_runs queue by design and are read as
throughput, not as latency; see the README.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..kaapana import KaapanaClient, is_finished, parse_time, series_uid_of, trigger_time
from ..model import HIGHER_IS_BETTER, NO_DIRECTION, Metric, Sample

NAME = "ingest"
DAG_ID = "service-process-incoming-dcm"
RESET_DAG_ID = "delete-series"

DICOM_PORT = "11112"
# Kaapana honours AE titles carrying the "kp-" prefix, up to 16 bytes; the wire
# silently truncates the rest.
PROJECT_AE = "kp-admin"
DATASET_AE = "kp-benchmark"

# dcmdump takes the files as arguments, so batches stay under the kernel's
# argv limit.
DUMP_BATCH = 200

SERIES_UID_TAG = "(0020,000e)"


def find_files(series_dir: Path, pattern: str) -> list[Path]:
    return sorted(f for f in series_dir.rglob(pattern) if f.is_file())


def series_uids(files: list[Path]) -> set[str]:
    """SeriesInstanceUIDs of *files*, top-level elements only.

    A SEG or RTSTRUCT carries its source series' UID inside a sequence, which
    dcmdump indents; that series is referenced, not ingested.
    """
    uids = set()
    for start in range(0, len(files), DUMP_BATCH):
        batch = [str(f) for f in files[start : start + DUMP_BATCH]]
        dump = subprocess.run(["dcmdump", *batch], capture_output=True,
                              text=True, check=False).stdout
        for line in dump.splitlines():
            if line.startswith(SERIES_UID_TAG) and "[" in line:
                uids.add(line.split("[")[1].split("]")[0])
    if not uids:
        raise RuntimeError(f"no SeriesInstanceUID found in {len(files)} file(s)")
    return uids


def send(host: str, paths: list[Path], pattern: str) -> None:
    print(f"  sending {len(paths)} path(s)")
    subprocess.run(
        ["dcmsend", host, DICOM_PORT, "--aetitle", DATASET_AE, "--call", PROJECT_AE,
         "--scan-directories", "--recurse", "--scan-pattern", pattern,
         *(str(d) for d in paths)],
        check=True,
    )

DEFAULT_SCENARIOS = "benchmark-scenarios.json"
DEFAULT_TIMEOUT_S = 1800
DEFAULT_FILE_PATTERN = "*.dcm"

METRICS = {
    "wall_seconds": Metric("ingest_wall_seconds", "seconds"),
    "throughput_series_per_second": Metric(
        "ingest_throughput_series_per_second", "series_per_second", HIGHER_IS_BETTER),
    "run_duration_p50_seconds": Metric("ingest_run_duration_p50_seconds", "seconds"),
    "run_duration_p95_seconds": Metric("ingest_run_duration_p95_seconds", "seconds"),
    "queue_delay_p50_seconds": Metric("ingest_queue_delay_p50_seconds", "seconds"),
    "peak_active_runs": Metric("ingest_peak_active_runs", "", NO_DIRECTION),
    "split_runs": Metric("ingest_split_runs", "", NO_DIRECTION),
    "failed_runs": Metric("ingest_failed_runs", "", NO_DIRECTION, invalidates_case=True),
    "dropped_series": Metric("ingest_dropped_series", "", NO_DIRECTION, invalidates_case=True),
}
TASK_DURATION = Metric("ingest_task_duration_seconds", "seconds")


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    paths: list[Path]
    timeout_s: int
    file_pattern: str


def load_scenarios(path: Path | None, data_dir: Path) -> list[Scenario]:
    """Read `{name: {"description": ..., "paths": [...]}}`, in declared order.

    Paths are dataset-relative and sent recursively, so one path is a single
    series directory or a whole modality directory.
    """
    if path is None:
        raise SystemExit(
            f"the ingest suite needs --scenarios, or a {DEFAULT_SCENARIOS} in {data_dir}"
        )
    document = json.loads(Path(path).read_text())
    if not isinstance(document, dict) or not document:
        raise ValueError(f"{path}: expected a non-empty object of scenario name -> definition")

    scenarios = []
    for name, spec in document.items():
        if not isinstance(spec, dict) or not spec.get("paths"):
            raise ValueError(f"{path}: scenario {name!r} needs a non-empty 'paths' list")
        directories = []
        for relative in spec["paths"]:
            directory = data_dir / relative
            if not directory.is_dir():
                raise ValueError(
                    f"{path}: scenario {name!r} has no {relative!r} under {data_dir}"
                )
            directories.append(directory)
        scenarios.append(Scenario(
            name=name,
            description=spec.get("description", ""),
            paths=directories,
            timeout_s=spec.get("timeout_s", DEFAULT_TIMEOUT_S),
            file_pattern=spec.get("file_pattern", DEFAULT_FILE_PATTERN),
        ))
    return scenarios


def wait_until_idle(client: KaapanaClient, timeout_s: int = 900,
                    poll_s: int = 15) -> bool:
    """Wait for the DAG to go quiet, so each scenario is timed on its own.

    Returns whether it settled.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if client.active_run_count(DAG_ID) == 0:
            return True
        time.sleep(poll_s)
    print("  ! platform did not go idle — this repetition starts from a dirty state")
    return False


def reset(client: KaapanaClient, uids: set[str], timeout_s: int = 1800,
          poll_s: int = 15) -> None:
    """Delete the series so every repetition ingests from the same state."""
    since = datetime.now(timezone.utc)
    print(f"  deleting {len(uids)} series")
    client.trigger_workflow(
        RESET_DAG_ID,
        sorted(uids),
        {"single_execution": False, "delete_complete_study": False},
    )
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        runs = client.dag_runs(RESET_DAG_ID, since)
        if runs and all(is_finished(r) for r in runs):
            return
        time.sleep(poll_s)
    raise TimeoutError(f"{RESET_DAG_ID} did not finish within {timeout_s}s")


def wait_for_runs(client: KaapanaClient, uids: set[str], since: datetime, timeout_s: int,
                  poll_s: int = 15, dropped_grace_s: int = 300) -> list[dict]:
    """Poll until every sent series has a finished run, or until the missing
    ones have clearly been dropped."""
    deadline = time.time() + timeout_s
    all_finished_since: float | None = None
    confirmed = False
    while time.time() < deadline:
        runs = [r for r in client.dag_runs(DAG_ID, since) if series_uid_of(r) in uids]
        finished = bool(runs) and all(is_finished(r) for r in runs)
        print(f"  {len(runs)}/{len(uids)} runs, "
              f"{sum(1 for r in runs if is_finished(r))} finished")

        if finished and len(runs) >= len(uids):
            # One extra poll: a series cut in two triggers a late second run
            # after the count already looks complete.
            if confirmed:
                return runs
            confirmed = True
        else:
            confirmed = False

        if finished and len(runs) < len(uids):
            all_finished_since = all_finished_since or time.time()
            if time.time() - all_finished_since > dropped_grace_s:
                print(f"  ! {len(uids) - len(runs)} series never triggered a run")
                return runs
        else:
            all_finished_since = None

        time.sleep(poll_s)
    raise TimeoutError(f"runs did not finish within {timeout_s}s")


def peak_active_runs(runs: list[dict]) -> int:
    events = []
    for run in runs:
        start, end = parse_time(run.get("start_date")), parse_time(run.get("end_date"))
        if start and end:
            events += [(start, 1), (end, -1)]
    peak = active = 0
    for _, change in sorted(events):
        active += change
        peak = max(peak, active)
    return peak


def run_durations(runs: list[dict]) -> list[float]:
    spans = [(parse_time(r.get("start_date")), parse_time(r.get("end_date"))) for r in runs]
    return [(end - start).total_seconds() for start, end in spans if start and end]


def queue_delays(runs: list[dict]) -> list[float]:
    """Trigger to start."""
    delays = []
    for run in runs:
        triggered = trigger_time(run)
        started = parse_time(run.get("start_date"))
        if triggered and started:
            delays.append(max(0.0, (started - triggered).total_seconds()))
    return delays


def task_durations(client: KaapanaClient, runs: list[dict]) -> dict[str, list[float]]:
    durations: dict[str, list[float]] = {}
    for run in runs:
        for task in client.task_instances(DAG_ID, run["dag_run_id"]):
            start, end = parse_time(task.get("start_date")), parse_time(task.get("end_date"))
            if start and end:
                durations.setdefault(task["task_id"], []).append((end - start).total_seconds())
    return durations


def measure(client: KaapanaClient, scenario: Scenario, host: str) -> list[Sample]:
    print(f"\n=== {scenario.name} === {scenario.description}")
    files = [f for d in scenario.paths for f in find_files(d, scenario.file_pattern)]
    if not files:
        raise RuntimeError(
            f"scenario {scenario.name!r}: no files matching {scenario.file_pattern!r}"
        )
    uids = series_uids(files)
    print(f"  {len(uids)} series, {len(files)} instances, {len(scenario.paths)} path(s)")

    wait_until_idle(client)
    reset(client, uids)

    since = datetime.now(timezone.utc)
    started = time.monotonic()
    send(host, scenario.paths, scenario.file_pattern)
    runs = wait_for_runs(client, uids, since, scenario.timeout_s)
    wall = time.monotonic() - started

    triggered = {series_uid_of(r) for r in runs}
    durations = run_durations(runs)
    delays = queue_delays(runs)
    peak = peak_active_runs(runs)

    values = {
        "wall_seconds": round(wall, 1),
        "throughput_series_per_second": round(len(triggered) / wall, 4),
        "peak_active_runs": peak,
        "failed_runs": sum(1 for r in runs if r["state"] == "failed"),
        "dropped_series": len(uids - triggered),
        "split_runs": len(runs) - len(triggered),
    }
    if durations:
        values["run_duration_p50_seconds"] = round(statistics.median(durations), 1)
        # Below 20 runs a p95 is the maximum wearing a percentile's name.
        if len(durations) >= 20:
            ordered = sorted(durations)
            values["run_duration_p95_seconds"] = round(ordered[int(0.95 * len(ordered)) - 1], 1)
    if delays:
        values["queue_delay_p50_seconds"] = round(statistics.median(delays), 1)

    print(f"  wall {wall:.0f}s, peak {peak} active, {values['dropped_series']} dropped")
    return [Sample(scenario.name, METRICS[key], value) for key, value in values.items()] + [
        Sample(f"{scenario.name}::{task}", TASK_DURATION, round(statistics.median(times), 1))
        for task, times in task_durations(client, runs).items()
    ]


def _scenarios(target) -> tuple[KaapanaClient, list[Scenario]]:
    if target.data_dir is None:
        raise SystemExit("the ingest suite needs --data-dir")
    scenarios = load_scenarios(target.scenarios, target.data_dir)
    client = KaapanaClient(target.host, target.username, target.password)
    return client, scenarios


def run(target) -> list[Sample]:
    client, scenarios = _scenarios(target)
    host = target.dicom_host
    samples: list[Sample] = []
    for scenario in scenarios:
        samples += measure(client, scenario, host)
    return samples


def warmup(target) -> None:
    """Ingest the smallest scenario once and throw the numbers away.

    The first ingestion after a deployment measures image pulls and cold
    caches, which is a different system.
    """
    client, scenarios = _scenarios(target)
    # Instances, not paths: one path can be a whole modality directory.
    smallest = min(scenarios, key=lambda s: sum(
        len(find_files(p, s.file_pattern)) for p in s.paths))
    print(f"\n--- warmup: {smallest.name} ---")
    measure(client, smallest, target.dicom_host)
