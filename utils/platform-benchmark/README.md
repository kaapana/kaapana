# Platform Benchmark

Benchmarks a **running Kaapana instance** and compares tagged results across
platform versions. Three suites:

| suite | what it measures | needs |
|---|---|---|
| `ingestion-pipeline` | timing of the ingestion DAG for a fixed DICOM scenario set | platform HTTPS APIs + dcmtk (`dcmsend`, `dcmdump`) |
| `internet` | ping / download / upload from inside the cluster (speedtest pod, `utils/internet-benchmark` image) | kubectl access |
| `gpu` | gpu_burn throughput + per-GPU health (`utils/nvidia-benchmark.yaml` image) | kubectl access |
| `helm` | how fast the machine deploys increasingly big helm charts (the kaapana-platform-chart timeout problem) | helm + kubectl access |

## Install

```bash
pip install -e .        # provides the `benchmark` command
# or: pip install -r requirements.txt && alias benchmark="python3 cli.py"
```

## Usage

```bash
export BENCHMARK_DATA_DIR=~/data/image_modalities   # or pass --data-dir each time

benchmark ingestion-pipeline --all --tag Version1 --password <pw>        # full suite: single + medium + max + trickle
benchmark ingestion-pipeline --tag Version1 --password <pw> --mode max   # just the 40-series flood
benchmark internet --tag Version1 --kubectl "ssh e230-pc11 microk8s kubectl"
benchmark gpu --tag Version1 --seconds 120 --kubectl "ssh e230-pc11 microk8s kubectl"
benchmark helm --tag Version1 --sizes 10,50,100
# ... redeploy a change, rerun with --tag Version2 ...
benchmark compare Version1 Version2   # % change heatmap PNG per shared suite
```

Every suite prints its metrics, stores them under `./results/<tag>.json` when
`--tag` is given (suites merge into the same tag file; change the location with
`benchmark --results-dir <dir> <suite> ...` or `BENCHMARK_RESULTS_DIR`), and
reprints all stored tags side by side. `compare` writes `results/compare_<suite>.png` — diverging
blue/red, red is always "worse" regardless of whether the metric is a time or
a throughput.

## Suite notes

**ingestion-pipeline** — four modes (`--mode`, default `all` runs them in
order), each scenario deletes its series (delete-series DAG) before sending
via `dcmsend` and waits for exactly the triggered
`service-process-incoming-dcm` runs:

| mode | scenario(s) | series |
|---|---|---|
| `single` | ct/seg/rtstruct/sm-single, sequentially | 1 each |
| `medium` | mixed-x15 (5 CT + 5 SEG + 5 SM) | 15 in parallel |
| `max` | max-x40 (10 CT + 10 SEG + 10 RTSTRUCT + 10 SM) | 40 in parallel |
| `trickle` | trickle-x5 (5 CT, 10 instances per chunk, 5s pause between chunks) | 5 slow senders |

`max` sends twice the DAG's `max_active_runs=20`, so the reported
`peak_active_runs` should equal 20 — it verifies the run cap is actually
saturated while `wall_s` shows how long two full batches take. `trickle`
simulates senders that dribble a series in over time: the 5s pause is below
the receiver's quiescence window, so every series must still land in exactly
one run — a nonzero `split_runs` (extra runs for an already-triggered series)
or `dropped_series` means the receiver cut a series apart mid-transfer. Each
scenario reports wall time, run p50/p95, scheduler gap p50, peak active runs,
dropped/split series and the slowest tasks.

**CI**: the repo's `platform_benchmarking` job (`.gitlab-ci.yml`) runs this
suite `BENCHMARK_RUNS`× (default 3) against the CI-deployed instance when
`CI_EXEC_BENCHMARKING=true` (with `CI_EXEC_DEPLOY=true`; on a fresh instance
also enable the integration tests so `first_login` sets the password). Each
repetition is tagged `<version>-r<i>`; results persist on the deploy-runner in
`$CI_BUILDS_DIR/kaapana-benchmark-results` across pipelines, so run 3× on the
base branch, 3× on the optimized branch (same runner = same hardware), and the
side-by-side table plus `benchmark compare <base> <new>` show the change.
`BENCHMARK_DATA_DIR` must be set as a CI/CD variable to an image_modalities
checkout on the runner. `--data-dir` (or `BENCHMARK_DATA_DIR`) is the image_modalities
repo root with `NSCLC/{CT,SEG,RTSTRUCT}/<patient>` (paired by folder name) and
`CDDP-EAGLE/SM/<patient>` — 10 patients each, giving the 40 distinct series.
TLS verification is disabled (self-signed platform certs). For a one-off
analysis of existing runs without the scenario set, `analyze.py` still works
standalone:

```bash
python3 analyze.py --password <pw> --send /path/to/dicom/dir
python3 analyze.py --password <pw> --limit 10 --json
```

**internet / gpu** — run a pod on the instance's cluster via `--kubectl`, which
is any command prefix that behaves like kubectl (e.g.
`"ssh <host> microk8s kubectl"`). The internet suite defaults to the DKFZ HTTP
proxy (`--proxy ''` to disable).

**helm** — generates a synthetic chart where each size unit is 1 ConfigMap
(~4 KB) + 1 Deployment + 1 Service (so `--sizes 10,50,100` submits 30/150/300
objects) and times `helm install --wait` / `helm uninstall --wait` per size.
Deployments default to 0 replicas — it measures helm/API-server/etcd handling
of big charts, not pod scheduling; `--replicas 1` also schedules pause pods.
Runs in its own namespace and always cleans up (release uninstalled, namespace
deleted) even on timeout. The chart is a local temp dir, so `--helm`/`--kubectl`
must run on the machine where the benchmark runs — for a remote instance use a
KUBECONFIG pointing at it.
