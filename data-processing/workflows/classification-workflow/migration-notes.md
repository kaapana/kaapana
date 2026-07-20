# Migration notes — classification-workflow

Migrated from `data-processing/processing-pipelines/classification-workflow/` (legacy
`KaapanaBaseOperator` style) to this Task API-based layout. This file records everything that could not
be cleanly migrated, every deliberate workaround/hardcode, and why — read this before changing or
deploying the two DAGs (`classification-training`, `classification-inference`).

## Reused containers (not migrated, already exist)

- `get-input-task` / `dicom-download` (→ legacy `GetInputOperator`)
- `mitk-tools` / `convert` (→ legacy `DcmConverterOperator(output_format="nrrd")`, confirmed equivalent by
  reading `mitk-tools/files/convert.sh`)

## Hard gaps — no Task API equivalent exists today

1. **No persistent cross-run volume mechanism.** `training` writes model checkpoints to
   `/models/<DAG_ID>/<WORKFLOW_ID>-fold-<FOLD>/` and TensorBoard logs to `/tensorboard/<RUN_ID>`;
   `inference` reads a checkpoint back from that same `/models` tree by `TASK_IDS`. `KaapanaTaskOperator`'s
   `IOMount`/`IOMapping` channel model only covers per-task-run I/O within a single DAG run — there's no
   channel that lets one DAG run's task write somewhere a *different, later* DAG run's task can read from.
   Both `/models` and `/tensorboard` are left as literal, unconverted host paths in `training.py`/
   `inference.py`/`classification_preprocessing.py`; whoever deploys this workflow must arrange for these
   paths to actually be mounted into the task pods some other way (there is no Task API-native way to do
   this yet).
2. **No dynamic, backend-populated "model picker."** The legacy inference DAG's `ui_forms.workflow_form`
   (`oneOf: []`, `models: True`, `kind: "classification"`) dynamically listed installed models for the user
   to pick from. `workflow.json.workflow_parameters` only supports statically-defined field types — there is
   no equivalent. **Workaround shipped:** the inference DAG's `TASK_IDS` workflow_parameter is a plain
   free-text string the user must type in manually (format:
   `<training-run-WORKFLOW_ID>-fold-<fold>/<model-best.pth.tar|model-end.pth.tar>`), restoring bare
   functionality at the cost of the nice picker UI.
3. **No Airflow run-identity env vars injected into task pods.** `KaapanaTaskOperator`'s `KAAPANA_ENVIRONMENT`
   constant (service URLs/credentials only) is everything it injects automatically — `RUN_ID`, `DAG_ID`,
   `TASK_ID`, `WORKFLOW_ID`, `WORKFLOW_NAME`, `TASK_IDS` are not among them, but the legacy scripts read all
   of these directly via `os.environ[...]`. **Workaround shipped:**
   - `DAG_ID` is statically knowable per DAG → hardcoded via `env=` in each `workflow_definition.py`.
   - `WORKFLOW_NAME` is statically knowable per DAG (used only to gate the inference-only branch in
     `classification_preprocessing.py`) → hardcoded via `env=`.
   - `WORKFLOW_ID`, `RUN_ID`, `TASK_IDS` are genuinely per-run values with no static substitute → exposed as
     required `workflow_parameters` so the user supplies them at trigger time. There is no enforced
     uniqueness — if a user reuses a `WORKFLOW_ID`/`RUN_ID`, a previous run's checkpoint/TensorBoard log gets
     silently overwritten. Legacy Airflow guaranteed `RUN_ID` uniqueness automatically; this is a real
     behavior regression, not just a documentation gap.
4. **`kaapanapy.helper.load_workflow_config()` cannot work under `KaapanaTaskOperator` at all.** It reads
   `<OperatorSettings().workflow_dir>/conf/conf.json` — a file that only ever existed because
   `KaapanaBaseOperator.execute()` mounted the entire legacy workflow directory and wrote the DAG-run `conf`
   object out to it (confirmed by reading `lib/kaapana_client/kaapana_client/helper/__init__.py` directly).
   There is no equivalent to fall back to; this is not the same class of gap as #1/#3 above, so it was
   actually fixed in code rather than left untouched:
   - `opensearch_helper.py` (both `training` and `inference`) previously did
     `project_form.get("opensearch_index", OpensearchSettings().default_index)` after calling
     `load_workflow_config()`. **Fixed:** now calls `OpensearchSettings().default_index` directly, with no
     `load_workflow_config()` call at all. This is not a loss of configurability — `OpensearchSettings`
     already reads `KAAPANA_DEFAULT_OPENSEARCH_INDEX`/`DEFAULT_INDEX` from the environment on its own, an
     override is still possible via an env var/`workflow_parameters` entry if ever needed. What *is* lost:
     a per-project-configured `opensearch_index` (from the DAG-run's `project_form`) is no longer honored —
     the container always uses the platform's configured default index.
   - `training.py`'s `sync_models_in_database()` previously built a `Project` HTTP header from
     `load_workflow_config()["project_form"]` before PUTting to the kaapana-backend's
     `/client/installed_models/sync`. **Fixed:** the `load_workflow_config()` call and `Project` header are
     removed; the PUT is now made without project scoping. `kaapana_client.services.ApiService`'s
     `KaapanaApiService`/`get_api_service_from_env()` was considered and rejected as a substitute — it drives
     an interactive OAuth2 device-code flow meant for a human at a CLI/notebook and would hang forever in an
     unattended task pod. **Not fully resolved**: if the backend enforces project scoping on this endpoint,
     the sync call may be rejected server-side; there is currently no non-interactive way to supply a project
     context from inside a `KaapanaTaskOperator` task pod.
   - `kaapanapy.helper.get_opensearch_client()` (also imported in `opensearch_helper.py`) is unaffected by any
     of this — verified by reading it directly, it only needs `OpensearchSettings`/`KeycloakSettings`/
     `ProjectSettings`, all backed by `KAAPANA_*`-prefixed env vars that `KaapanaTaskOperator` does inject.
     Left untouched, no fix needed.
5. **`SERVICES_NAMESPACE` naming mismatch.** `opensearch_helper.py` (untouched) reads the unprefixed
   `os.environ["SERVICES_NAMESPACE"]`, but `KaapanaTaskOperator` only injects the `KAAPANA_`-prefixed
   `KAAPANA_SERVICES_NAMESPACE`. **Workaround shipped:** `SERVICES_NAMESPACE` is declared as a template `env`
   default (`"services"`, the correct real-cluster value) in both `classification-training/files/
   processing-container.json` and `classification-inference/files/processing-container.json`, so the bare
   read doesn't `KeyError`. This doesn't address gap #4 above, just prevents an immediate crash on this one
   line.
6. **`single_execution`** (present in both legacy `ui_forms` blocks) is not read by any processing script in
   this workflow — it looks like a `KaapanaBaseOperator`-native batch-vs-per-item execution toggle with no
   `KaapanaTaskOperator` equivalent. Dropped from both `workflow.json` files.
7. **GPU resources.** Legacy `TrainingOperator`/`InferenceOperator` set `gpu_mem_mb=11000`. There is no
   confirmed convention for expressing GPU resource requests in the new `pc_models.Resources` model anywhere
   in this repo (no existing new-style container declares GPU resources) — both `classification-training`
   and `classification-inference`'s `processing-container.json` only set `resources.requests.memory:
   "16000Mi"`, no GPU request. Needs a manual decision once a GPU-resource convention exists elsewhere.
8. **`KaapanaTaskOperator(resources=...)` has no confirmed working precedent and was rejected in an actual
   deployment.** The operator's Python signature (as checked out in this repo) does accept a `resources:
   Optional[pc_models.Resources]` constructor kwarg, but neither of this repo's two real, previously-working
   examples (`registration-workflow`, `dummy-workflow`) ever use it, and passing it caused a real failure when
   this workflow was actually deployed. **Fix applied:** removed `resources=` from every `KaapanaTaskOperator`
   call in both `workflow_definition.py` files — resource sizing is expressed only via each container's own
   `processing-container.json` template `resources` field, which is unambiguously supported and is where the
   two real working examples set it.
9. **Real `task_api` library bug: `processing-container.json` `resources.requests` without `resources.limits`
   crashes on real deployment.** `task_api.processing_container.resources.compute_memory_resources()` (used
   by `KubernetesRunner`, i.e. the real-cluster path, not `DockerRunner`'s local-testing path — this is why
   local container testing during the initial migration never caught it) unconditionally calls
   `task_resources.limits.get("memory")`; if a template sets `requests` without `limits`, `.limits` is `None`
   and this raises `AttributeError`. **Fix applied:** all three containers' `processing-container.json` now
   set both `requests.memory` and `limits.memory` (preprocessing: 4000Mi/8000Mi; training/inference:
   16000Mi/18000Mi). Verified directly by calling `compute_memory_resources()` against each fixed template in
   a Python REPL (not just schema validation, which doesn't exercise this function) — all three now compute
   successfully instead of crashing.

## Env vars needing a value that KaapanaTaskOperator doesn't supply automatically

For every processing-container in this workflow, every `os.environ[...]` read in the shipped script has a
corresponding declared default in that container's `processing-container.json` `env[]` (so nothing
`KeyError`s even if never overridden) — see gap #3 above for which ones are additionally exposed as
`workflow_parameters` for the user to actually set per run.

## Required `workflow_parameters` not derived from `ui_forms` (infrastructure wiring, not legacy fields)

- `download` task, `DATASET` (`get-input-task`/`dicom-download`'s own env schema has no usable default for
  this — the template ships `""`, and there's no platform-level auto-fill for "which dataset to download,"
  unlike its other env vars which line up with platform-injected `KAAPANA_*` values). Present in both DAGs'
  `workflow.json`, `ui_form.type: "dataset"` (a real dataset picker, not free text).
- `training`/`inference`/`preprocessing` tasks: `WORKFLOW_ID`, `RUN_ID`, `TASK_IDS` — see gap #3.

## What was tested

`classification-preprocessing`, `classification-training`, `classification-inference` were each built and
run standalone against real DICOM→nrrd→preprocessed `.npy` fixtures (see the migration conversation/PR
description for exact commands); OpenSearch was mocked for `training`/`inference` since no live instance was
available locally. `workflow_definition.py`/`workflow.json`/`extension_manifest.json` were validated
(`py_compile`, JSON parse, `task_api.cli validate --schema pc`, `extensionctl build`).

After the `resources=`/env-var/`resources.limits`/`load_workflow_config()` fixes above (found via an actual
deployment attempt, not by local testing — local testing never exercises `KaapanaTaskOperator.execute()` or
`KubernetesRunner`, only `DockerRunner`/raw `docker run`), the following were re-verified:
- All three containers rebuilt cleanly with the fixed `processing-container.json`/scripts.
- `compute_memory_resources()` (the function that actually crashed on missing `resources.limits`) was called
  directly against each container's fixed template in a Python REPL — all three now succeed.
- `training` was re-run end-to-end against the same fixtures (OpenSearch still mocked): it still produces a
  real checkpoint, and the previously-crashing `sync_models_in_database()` call now fails only on a plain
  network-connection error trying to reach `kaapana-backend-service.services.svc` (expected — no such service
  exists in this local sandbox) instead of crashing inside `load_workflow_config()`/`OperatorSettings()`
  itself — confirming the code-level bug is gone, though the network call itself was not verified against a
  real backend.
- `opensearch_helper.py`'s fix (dropping `load_workflow_config()` for `opensearch_index`) was **not**
  independently re-run, since every local container test mocks `opensearch_helper.py` entirely (there's no
  local OpenSearch to test against) — its correctness rests on reading `OpensearchSettings`'s source directly,
  not on an observed run. Flagging this rather than overclaiming it as tested.

The DAGs themselves (`workflow_definition.py` as actually interpreted by `KaapanaTaskOperator.execute()`)
were still not run against a live Airflow/Kubernetes cluster after these fixes — that verification requires
an actual deployment, which is outside what this migration could do locally.
