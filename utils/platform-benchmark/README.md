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

Everything runs through one command; `--suite` and `--scenario` are repeatable,
`--runs N` repeats the whole selection N times. Results are printed as JSON.
With `--out DIR` the run also writes:

* `results.json` — the same structure, `{suite: {run: metrics}}`
* `metrics.txt` — OpenMetrics, e.g.
  `kaapana_ingest_run_p50_s{run="1",scenario="max"} 120.5`, with `run` and
  `scenario` (and `item` for per-task values) as labels. Non-numeric fields
  (`error`, `server`) stay in `results.json` only.

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

`root_path` is whatever subdirectory of the dataset repo these scenarios were
written against — `""` means `--data-dir` itself. Each scenario entry is a
directory under `--data-dir/root_path`, sent whole with
`dcmsend --scan-directories --recurse`. Patient directories and whole modality
directories mix freely, so how many series a scenario produces is decided by
what is on disk, not by the benchmark. The series actually sent are counted
from the SeriesInstanceUIDs `dcmdump` finds, which is what `dropped_series` and
`split_runs` are measured against.

`--scenario-file` is required for the ingest suite and has no default. The
definitions are configuration, so they live in neither repository: CI reads
them from the `CI_EXEC_BENCHMARK_SCENARIOS` pipeline variable (overridable per
run), and locally you keep a JSON file wherever you like. A scenario file is
only meaningful paired with the `--data-dir` it was written against — a
mismatch fails with the exact missing directory, not silently.

## Suite notes

**ingest** — each scenario deletes its series (delete-series DAG, skip with
`--no-reset`), sends via `dcmsend` and waits for exactly the
`service-process-incoming-dcm` runs those series trigger. Reported per
scenario: `wall_s`, `run_p50_s`/`run_p95_s`, `sched_gap_p50_s` (scheduler dead
time per run), `peak_active_runs`, `failed_runs`, `dropped_series`,
`split_runs`, `task_p50_s` (three slowest tasks), `failed_scenario`.

A scenario sending more series than the DAG's `max_active_runs=20` should
report `peak_active_runs` equal to that cap, while `wall_s` shows how long the
batches take. `split_runs` above zero means the receiver cut a series apart
mid-transfer (its settle timer fired before the last instance arrived);
`dropped_series` counts series that were accepted but never triggered a run.
`--timeout-h` (default 4) bounds the wait for a scenario's runs. TLS
verification is disabled (self-signed platform certs).

**internet / gpu** — run a pod on the instance's cluster via `--kubectl`, which
is any command prefix that behaves like kubectl (e.g.
`"ssh <host> microk8s kubectl"`). The internet suite defaults to the DKFZ HTTP
proxy (`--proxy ''` to disable).

**helm** — generates a synthetic chart where each size unit is 1 ConfigMap
(~4 KB) + 1 Deployment + 1 Service (sizes 10/50/100 submit 30/150/300 objects)
and times `helm install --wait` / `helm uninstall --wait` per size. Deployments
have 0 replicas — it measures helm/API-server/etcd handling of big charts, not
pod scheduling. Runs in its own namespace and always cleans up (release
uninstalled, namespace deleted) even on timeout. The chart is a local temp dir,
so `--helm` must reach the cluster from where the benchmark runs.

## CI

`benchmark_platform` (`ci/pipeline/benchmark.yml`) runs against the
CI-deployed instance when the `exec_benchmark` pipeline input is true, together
with `exec_deploy`; on a fresh instance also enable `exec_integration_tests`, so
`first_login` sets the password the job logs in with. `CI_EXEC_BENCHMARK_ARGUMENTS`
(default `--suite ingest --runs 3`) is appended to the `benchmark run` call, so
it carries `--suite`, `--scenario` and `--runs`.

`CI_EXEC_BENCHMARK_SCENARIOS` is a pipeline variable holding the scenario JSON
(`root_path` + scenarios); the job writes it to a file and passes that as
`--scenario-file`, so it can be swapped per run instead of only in project
settings. Which scenarios run is `--scenario` in `CI_EXEC_BENCHMARK_ARGUMENTS`,
what they are is this variable. `preflight_variables` rejects a run with
`exec_benchmark` and no `scenarios` object in it.

`results.json` and `metrics.txt` are job artifacts; `metrics.txt` is also
published as GitLab's `artifacts:reports:metrics`. Nothing is kept on the
runner between pipelines.

The job clones the dataset repo (git-lfs) from `CI_EXEC_BENCHMARK_DATA_REPO_URL`
into `$CI_BUILDS_DIR/<repo name>` the first time it runs on a given runner,
authenticating with `CI_EXEC_BENCHMARK_DATA_REPO_TOKEN` (a masked, read-only
project/group CI/CD variable); later runs reuse that clone. `--data-dir` is
that clone's root — `root_path` in the scenario JSON picks the subdirectory
within it. The job allows 8 hours, more than the 4 hours `--timeout-h` gives a
single scenario.
