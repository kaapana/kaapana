# Platform Benchmark

Measures a running Kaapana instance and writes the numbers out.

## Prerequisites

- a deployed Kaapana instance and its `kaapana` password
- `dcmtk` on PATH (`dcmsend`, `dcmdump`)
- a DICOM dataset, plus a scenario file naming what to send from it
- `pip install -e .`

## Run

```bash
export BENCHMARK_PASSWORD=<pw>

benchmark run --host https://<instance> \
  --data-dir ~/data/image_modalities \
  --scenarios scenarios.json \
  --out-dir results
```

Writes `benchmark.json` (every repetition's raw value, plus the environment it
ran in) and `benchmark.md` (the same numbers as a table).

| flag | default | |
|---|---|---|
| `--suite` | `ingest` | repeatable: `ingest`, `internet`, `gpu`, `helm` |
| `--repeat` | 3 | measured repetitions |
| `--warmup` | 1 | repetitions run and discarded first |
| `--kubectl` | `kubectl` | prefix reaching the cluster, e.g. `"ssh host microk8s kubectl"` — needed by `internet`, `gpu` and `helm` |
| `--username` | `kaapana` | |
| `--profile` | `workstation` | class of machine, recorded with the results |

Connects without TLS verification, for the self-signed platform certificate.

## Scenarios

What the ingest suite sends, in declared order. Paths are relative to
`--data-dir` and sent recursively, so a path is one series directory or a whole
modality directory.

```json
{
  "low":  { "description": "one CT series",      "paths": ["NSCLC/CT/LUNG1-001"] },
  "high": { "description": "everything at once", "paths": ["NSCLC/CT", "NSCLC/SEG"] }
}
```

| key | default | |
|---|---|---|
| `paths` | required | |
| `description` | empty | printed with the scenario |
| `timeout_s` | 1800 | how long to wait for the triggered runs |
| `file_pattern` | `*.dcm` | which files to send |

## How many repetitions?

Each run reports a `suggested runs` column from the spread it observed, for a
median within ±10%: `n = (1.96 · cv / 0.10)²`. Run three, read the column, raise
`--repeat` where it asks for more.

Scenarios that dropped or failed work are marked invalid.

## CI

`benchmark_platform` (`ci/pipeline/benchmark.yml`) runs against the CI-deployed
instance, after `CI_EXEC_DEPLOY` and `CI_EXEC_INTEGRATION_TESTS`: `first_login`
sets the password it logs in with.

| variable | |
|---|---|
| `CI_EXEC_BENCHMARK` | the toggle; the **`Benchmark`** MR label sets it to `true` |
| `BENCHMARK_CONFIG` | File-type variable holding dataset, login, suites and scenarios — see [`ci/benchmark.config.example`](../../ci/benchmark.config.example) |
| `BENCHMARK_DATA_REPO_TOKEN` | masked variable with `read_repository` on the dataset repo |

Results are job artifacts only.
