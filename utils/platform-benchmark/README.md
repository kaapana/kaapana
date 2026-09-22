# Platform Benchmark

Benchmarks a **running Kaapana instance** and reports the numbers as JSON plus
OpenMetrics. Four suites:

| suite | what it measures | needs |
|---|---|---|
| `ingest` | timing of the ingestion DAG for the scenarios of the dataset | platform HTTPS APIs + dcmtk (`dcmsend`, `dcmdump`) |
| `internet` | ping / download / upload from inside the cluster (speedtest pod, `klakadkfz/speedtest` image) | kubectl access |
| `gpu` | gpu_burn throughput + per-GPU health (`chrstnhntschl/gpu_burn` image) | kubectl access |
| `helm` | how fast the machine deploys increasingly big helm charts (the kaapana-platform-chart timeout problem) | helm + kubectl access |

## Install

```bash
pip install -e .        # provides the `benchmark` command
```

## Usage

```bash
export BENCHMARK_DATA_DIR=~/data   # dataset repo root; or pass --data-dir each time

benchmark run --suite ingest --host https://<instance> --password <pw> --scenario-file scenarios.json
benchmark run --suite ingest --scenario-file scenarios.json --scenario minimal --scenario max --runs 3
benchmark run --suite internet --suite gpu --kubectl "ssh e230-pc11 microk8s kubectl"
benchmark run --suite helm --helm "ssh e230-pc11 microk8s helm" --kubectl "ssh e230-pc11 microk8s kubectl"
```

- One command for everything; `--suite` and `--scenario` are repeatable,
  `--runs N` repeats the whole selection N times.
- Results are printed as JSON. With `--out DIR` the run also writes:
  - `results.json` — same structure, `{suite: {run: metrics}}`
  - `metrics.txt` — OpenMetrics, e.g.
    `kaapana_ingest_run_p50_s{run="1",scenario="max"} 120.5`, labels `run` and
    `scenario` (plus `item` for per-task values). Non-numeric fields (`error`,
    `server`) stay in `results.json` only.

## Scenarios

`root_path` plus a name and the directories each scenario sends, both
relative to `--data-dir/root_path`:

```json
{
  "root_path": "image_modalities",
  "scenarios": {
    "minimal": ["NSCLC/CT/LUNG1-001", "NSCLC/SEG/LUNG1-001", "NSCLC/RTSTRUCT/LUNG1-001"],
    "ct-seg": ["NSCLC/CT", "NSCLC/SEG"],
    "max": ["NSCLC/CT", "NSCLC/SEG", "NSCLC/RTSTRUCT", "CDDP-EAGLE/SM"]
  }
}
```

- `root_path` is the subdirectory of the dataset repo these scenarios were
  written against — `""` means `--data-dir` itself.
- Each scenario entry is a directory under `--data-dir/root_path`, sent whole
  with `dcmsend --scan-directories --recurse`.
- Patient and modality directories mix freely; how many series a scenario
  produces is decided by what's on disk, not the benchmark.
- Series actually sent are counted from the SeriesInstanceUIDs `dcmdump`
  finds — what `dropped_series` and `split_runs` are measured against.
- `--scenario-file` is required for the ingest suite, no default. Definitions
  live in neither repository: CI reads them from the `scenarios` key of the
  `BENCHMARK_DATA_CONFIG` project CI/CD variable; locally, any JSON file.
- A scenario file is only meaningful paired with the `--data-dir` it was
  written against — a mismatch fails with the exact missing directory.

## Suite notes

### ingest

- Each scenario deletes its series (delete-series DAG, skip with
  `--no-reset`), sends via `dcmsend`, waits for exactly the
  `service-process-incoming-dcm` runs those series trigger.
- Per scenario: `wall_s`, `run_p50_s`/`run_p95_s`, `sched_gap_p50_s`
  (scheduler dead time per run), `peak_active_runs`, `failed_runs`,
  `dropped_series`, `split_runs`, `failed_scenario`.
- Per DAG task (all tasks, keyed by task_id): `task_count`,
  `task_p50_s`/`task_p95_s`/`task_avg_s`, `task_phase_{queue,setup,spawn,code}_s`,
  `critical_path` (slowest root-to-leaf task_ids).
- `peak_active_runs` caps at the DAG's `max_active_runs=20`; `wall_s` shows
  how long the batches take.
- `split_runs` > 0 means the receiver cut a series apart mid-transfer (settle
  timer fired early); `dropped_series` counts series accepted but never
  triggering a run.
- `--timeout-h` (default 4) bounds the wait per scenario. TLS verification is
  disabled (self-signed platform certs).

### internet / gpu

- Run a pod on the instance's cluster via `--kubectl`, any command prefix
  behaving like kubectl (e.g. `"ssh <host> microk8s kubectl"`).
- `internet` defaults to the DKFZ HTTP proxy (`--proxy ''` to disable).

### helm

- Generates a synthetic chart: each size unit is 1 ConfigMap (~4 KB) + 1
  Deployment + 1 Service (sizes 10/50/100 submit 30/150/300 objects), times
  `helm install --wait` / `helm uninstall --wait` per size.
- Deployments have 0 replicas — measures helm/API-server/etcd handling of big
  charts, not pod scheduling.
- Runs in its own namespace, always cleans up (release uninstalled, namespace
  deleted) even on timeout.
- The chart is a local temp dir, so `--helm` must reach the cluster from
  where the benchmark runs.
