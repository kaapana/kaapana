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

1. **No persistent cross-run volume mechanism — since resolved at the operator level.** Originally,
   `training` wrote model checkpoints to `/models/<DAG_ID>/<WORKFLOW_ID>-fold-<FOLD>/` and TensorBoard logs
   to `/tensorboard/<RUN_ID>` as literal, unconverted host paths — `KaapanaTaskOperator`'s `IOMount`/
   `IOMapping` channel model only covers per-task-run I/O within a single DAG run, so there was no
   Task API-native way to make either path actually resolve to real, persistent storage inside a task pod.
   **Resolved:** `KaapanaTaskOperator._create_task` (`services/base/workflow-api/.../KaapanaTaskOperator.py`)
   now unconditionally mounts two additional PVCs into every task pod, alongside the pre-existing `dshm`
   `emptyDir`: `models-pv-claim` at `/models` and `tensorboard-pv-claim` at `/tensorboard`, both read-write,
   both shared (no per-run/per-project `sub_path`). This is a platform-level fix outside this workflow's own
   files — it applies to every `KaapanaTaskOperator` task pod, not just this workflow's. As a direct
   consequence:
   - `inference.py`'s existing `/models/classification-training/...` `TASK_IDS` read (unchanged, still not
     touched by this workflow) now resolves to real, persistent, cross-DAG-run storage instead of a phantom
     path — gap #2 below (the free-text `TASK_IDS` workaround) is otherwise unaffected.
   - `training.py`'s own `/tensorboard/<RUN_ID>` write (unchanged) is now genuinely persisted too.
   - Model checkpoints specifically are **not** written into `/models` by `training` itself anymore — see
     "Post-migration changes" below for the `training` → `persist-model` split that now owns that write.
2. **No dynamic, backend-populated "model picker."** The legacy inference DAG's `ui_forms.workflow_form`
   (`oneOf: []`, `models: True`, `kind: "classification"`) dynamically listed installed models for the user
   to pick from. `workflow.json.workflow_parameters` only supports statically-defined field types — there is
   no equivalent. **Workaround shipped (superseded):** the inference DAG's `TASK_IDS` workflow_parameter was
   a plain free-text string the user had to type in manually (format:
   `<training-run-WORKFLOW_ID>-fold-<fold>/<model-best.pth.tar|model-end.pth.tar>`), restoring bare
   functionality at the cost of the nice picker UI. **Resolved 2026-07-21** — see "Dynamic model picker for
   classification-inference" below for the real fix (a new `ModelUIForm` type plus a `model-download` task).
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
   - `persist_model.py`'s `sync_models_in_database()` (originally part of `training.py`, then split out into
     its own `persist-model` container/task — see "Post-migration changes" below) previously built a
     `Project` HTTP header from `load_workflow_config()["project_form"]` before PUTting to the
     kaapana-backend's `/client/installed_models/sync`. An intermediate version of this migration removed the
     `load_workflow_config()` call and the `Project` header entirely and made the PUT without project
     scoping — this was deployed and confirmed broken: the backend *does* enforce project scoping on this
     endpoint (`sync_installed_models` in
     `services/base/kaapana-backend/docker/files/app/workflows/routers/client.py` depends on `get_project`
     in `app/dependencies.py`, which 400s with `"Missing Project header"` if the header is absent), observed
     on an actual cluster deployment of this DAG (`dag_id=classification-training_inc1`,
     `run_id=manual__2026-07-20T13:54:37...`): training completed and saved a checkpoint, but the task still
     failed with `sync_models_in_database failed [400]: {"detail":"Missing Project header"}`.
     **Actually resolved:** the claim above that there is "no non-interactive way to supply a project context
     from inside a `KaapanaTaskOperator` task pod" was an investigation gap, not a real platform limitation —
     `airflow_adapter.py`'s `submit_workflow_run` (confirmed by reading it and by `git blame`, predating this
     migration) already injects `KAAPANA_PROJECT_IDENTIFIER` (the triggering DAG run's project id) into every
     task's env unconditionally, for every task in every DAG. The already-migrated
     `registration-workflow`'s `download` task (`download_dicoms.py`) already relies on exactly this and
     demonstrates the fix: read `KAAPANA_PROJECT_IDENTIFIER`, `GET {KAAPANA_AII_URL}/projects/{identifier}` to
     resolve the full project object, then send it as `headers={"Project": json.dumps(project)}`.
     `persist_model.py` now follows the same pattern via a local `get_project()` helper (same signature as
     `download_dicoms.py`'s); `KAAPANA_PROJECT_IDENTIFIER` is declared in `processing-container.json`'s `env[]`
     (empty default — always overridden by the platform injection above) so the read doesn't silently pass
     `None` if ever run outside that injection path. `kaapana_client.services.ApiService`'s
     `KaapanaApiService`/`get_api_service_from_env()` remains correctly rejected as a substitute — it drives an
     interactive OAuth2 device-code flow meant for a human at a CLI/notebook and would hang forever in an
     unattended task pod; it was never needed here. Separately worth knowing if changing sync semantics later:
     `crud.update_installed_models` (`app/workflows/crud.py`) does a full delete-then-recreate of all
     `InstalledModel` rows scoped to `(project_id, kind)` per call — it is not an upsert, so whatever
     `installed_models` dict is PUT on a given call becomes the *entire* registered set for that project+kind,
     not a merge into it.
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

The `training`/`persist-model` split and the `models`/`tensorboard` PVC mounts (see gap #1 and
"Post-migration changes") were verified only as far as: `training.py`/`persist_model.py` both `py_compile`
clean, and both containers' `processing-container.json` pass `task_api.cli validate --schema pc`. Neither
`persist-model` nor the new `model` `IOMapping` between `training` and `persist-model` have been run
end-to-end — against fixtures locally or on the real cluster — as of this change.

## Post-migration changes

- **`classification-training` split into `training` + `persist-model` tasks (two processing-containers),
  wired via a Task API `IOMapping` output/input channel.** `training.py` originally trained the model,
  wrote the checkpoint directly to `/models/<DAG_ID>/<WORKFLOW_ID>-fold-<FOLD>/`, and then called
  `sync_models_in_database()` to PUT the newly installed checkpoints to the kaapana-backend, all in one
  script. This coupled a long-running GPU job to both a filesystem convention and a network call, and on an
  actual deployment the network call's failure (see gap #4 above — `"Missing Project header"`) made the
  whole `training` task report as failed even though the model had already trained and saved successfully.
  - `training` is no longer responsible for persisting into the shared `/models` volume at all. It writes
    its checkpoint(s) (`model-best.pth.tar`/`model-end.pth.tar`), `config.json`, and `training.log` to a new
    `model` **output channel** (`processing-container.json` → `templates[].outputs`, `mounted_path:
    "/kaapana/app/model"` — the same Task API-native mechanism `download`→`convert`→`preprocessing`→
    `training` already used for `downloads`/`nrrd`/`preprocessed`). `training.py`'s `RESULTS_DIR` now points
    there directly (`/kaapana/app/model`, flat — no `<DAG_ID>/<WORKFLOW_ID>-fold-<FOLD>` nesting needed,
    since the channel's underlying storage is already namespaced per run+task by `KaapanaTaskOperator`
    itself). Since `training` no longer builds a `/models/<DAG_ID>/...` path, its `DAG_ID` env var was
    removed (from both `processing-container.json` and `workflow_definition.py`) — nothing in `training.py`
    reads it anymore. `WORKFLOW_ID` is still required: it's written into `config.json` as metadata for
    `persist-model` to read back.
  - `_get_installed_classification_models()` and `sync_models_in_database()` were moved verbatim into a new,
    separate **`persist-model`** processing-container (renamed from an earlier, never-shipped
    `classification-model-sync`; `processing-containers/persist-model/files/persist_model.py`), run as a new
    `persist-model` task after `training` (`training >> persist_model` in
    `classification-training/workflow_definition.py`), connected by an actual `IOMapping`
    (`upstream_output_channel="model"` → `input_channel="model"`) rather than a shared hardcoded path.
    `persist-model` does two things in sequence, matching its name: (1) `persist_model()` reads the
    `model`-channel-mounted directory's `config.json` for `WORKFLOW_ID`/`FOLD` and copies its contents into
    `/models/<DAG_ID>/<WORKFLOW_ID>-fold-<FOLD>/` — this is now a real write, since (see gap #1 above)
    `KaapanaTaskOperator` mounts a genuine `models-pv-claim` PVC at `/models`; (2) `sync_models_in_database()`
    (unchanged from before) re-scans the whole `/models/<DAG_ID>` tree and PUTs the accumulated set to the
    kaapana-backend — still subject to the unresolved "Missing Project header" gap above, but that failure
    no longer masks `training`'s own success/failure status.
  - `persist-model` uses `local-only/base-python-cpu:latest` (not the GPU base `training`/`inference` use)
    since it does no ML work, only a filesystem copy + one HTTP PUT.
  - TensorBoard logs remain unhandled by this split, as before — `training.py` still writes them to
    `/tensorboard/<RUN_ID>` and nothing downstream consumes them. Unlike the model checkpoint, this path was
    left as-is rather than routed through an output channel, since nothing in this DAG needs to read
    TensorBoard logs back (they're for a human to open directly, e.g. via the `tensorboard-pv-claim` mount).

## 2026-07-21 — Dynamic model picker for classification-inference (resolves gap #2)

Gap #2 above (no dynamic, backend-populated model picker; `TASK_IDS` on `preprocessing`/`inference` was a
free-text field) is resolved. Scope is limited to the **inference** DAG — training doesn't select a model and
was not changed.

- **New `model-download` processing-container** (`processing-containers/model-download/`), wired as a source
  task (like `download`, no `iochannel_maps`) in `classification-inference`'s DAG only. It reads a `TASK_IDS`
  env var (the same `<WORKFLOW_ID>-fold-<FOLD>/<model-best.pth.tar|model-end.pth.tar>` string `persist-model`
  already produces and registers) and copies exactly that checkpoint plus its sibling `config.json` from the
  hardcoded `/models/classification-training/` prefix into a new `model` output channel
  (`/kaapana/app/model`) — the only task in this workflow that still touches `/models` directly. No network
  call needed: `task_ids` is a self-sufficient relative path once combined with that hardcoded prefix.
- **`preprocessing` and `inference` no longer read `/models` themselves.** Both gained a second `IOMapping`
  (`model_download`'s `model` output → their own `model` input channel) alongside their existing channels.
  `inference.py` now reads `config.json` and globs for the one `*.pth.tar` file under its `model` input
  channel instead of hardcoding `/models/classification-training/<TASK_IDS>`; `classification_preprocessing.py`'s
  existing `WORKFLOW_NAME`-gated inference-only branch does the same for `config.json`'s `PATCH_SIZE`. Since
  `classification-preprocessing`'s template/image is shared with the training DAG, the new `model` input
  channel is declared on the template but only ever wired via `IOMapping` on the inference DAG — confirmed
  safe by reading `merge_io_channels` (`lib/task_api/task_api/processing_container/common.py:101-126`)
  directly: a template input channel with no matching `IOVolume` simply produces no `IOChannel` (no error),
  so the training DAG's `preprocessing` task — which never takes the `WORKFLOW_NAME`-gated branch that would
  read it — is unaffected by the channel being declared but unmounted there.
- **`inference.py`'s dead `DAG_ID`/`RUN_ID`-driven `RESULTS_DIR` line** (created a directory, never read it
  again — the real checkpoint path was already built from a hardcoded string, not `DAG_ID`) **was removed**,
  along with the now-fully-unused `DAG_ID`/`RUN_ID`/`TASK_IDS` env vars and workflow_parameters on the
  inference DAG's `inference`/`preprocessing` tasks.
- **New `ModelUIForm` type** (`type: "model"`, optional `kind` field to scope by installed-model kind) added
  to `services/base/workflow-api/docker/files/app/schemas.py`'s `UIForm` union — the actual dynamic-picker
  mechanism this gap needed, following the same minimal-discriminator shape as the existing `DatasetUIForm`.
  Confirmed this workflow installs via `extension-manager-service`'s `WorkflowInstaller`
  (`services/base/extension-manager-service/docker/files/app/v1/services/dispatch/consumers/workflows.py`),
  which forwards `workflow.json` as a raw dict straight to workflow-api's `POST /workflows` with no
  validation of its own — so only `services/base/workflow-api`'s schema needed updating for this workflow.
  (There is a separate, unrelated `data-processing/workflows/workflow-installer/` Kubernetes-Job mechanism
  with its own duplicate `UIForm` schema copy, used only by Helm-installed "core" workflows like
  `dummy-workflow`/`registration-workflow` under `kaapana-workflows-core` — it has no code path to/from
  extension-manager-service and does not need updating for this OCI-extension-installed workflow. Worth
  checking if this ever needs to apply to a Helm-installed core workflow instead.)
- **New kaapana-backend endpoint `GET /client/installed_models`** (`kind` query param, project-scoped via the
  existing `get_project` dependency), added next to the existing `PUT /client/installed_models/sync` in
  `services/base/kaapana-backend/docker/files/app/workflows/routers/client.py`. Delegates to
  `crud.get_installed_models_by_project`, which already existed but was previously only used internally by a
  different legacy feature (`replace_installed_models_in_schemas`, for the legacy JSON-schema `workflow_form`
  generation). No DB migration needed — `kind`/`task_ids`/`friendly_name`/`project_id` all already existed on
  `InstalledModel`.
- **Frontend** (`services/base/workflow-ui`): `ModelUIForm`/`InstalledModel` types added to
  `types/schemas.ts`; new `api/modelsApiClient.ts` (mirrors `datasetsApiClient.ts` exactly — separate axios
  instance against `VITE_KAAPANA_BACKEND_URL`); `components/WorkflowForm.vue` gained a `model` field branch
  mirroring the existing `dataset` branch (`item-value="task_ids"`, so the value bound into the trigger
  form's `TASK_IDS` env var is exactly what `model-download` needs), with loading state keyed per `kind`
  (unlike datasets, which have no filter dimension) since a workflow could in principle declare `model`
  parameters of more than one kind.
- `workflow.json` (classification-inference only): removed the `preprocessing`/`TASK_IDS`,
  `inference`/`TASK_IDS`, and `inference`/`RUN_ID` entries; added one entry — `task_title: "model-download"`,
  `env_variable_name: "TASK_IDS"`, `ui_form.type: "model"`, `ui_form.kind: "classification"`.

**What was tested:** `task_api.cli validate --schema pc` on all three touched/new `processing-container.json`
files; `py_compile` on all touched/new Python; a direct Pydantic construction of the updated `workflow.json`
against workflow-api's own `WorkflowCreate` (the actual schema the real extension-manager install path
validates against — this exercises the one gate that matters for this workflow); `vue-tsc --build` and
`eslint` on the frontend changes (zero new errors — the pre-existing `no-explicit-any`/`no-empty-object-type`
lint debt elsewhere in this frontend predates this change and was left alone).

**Not tested:** `model_download.py`'s actual `/models` read end-to-end (the Task API CLI can't mount a
non-channel path — see `task-api-contract.md`'s known-issues section — this needs a plain
`docker run -v <fixture>:/models:ro ...` or a real deployment); the DAG end-to-end on a live
Airflow/Kubernetes cluster; the new kaapana-backend endpoint against a real database.

**Known limitations, flagged not fixed:**
- `model-download` does no existence check before copying — a stale/renamed `task_ids` value (e.g. an
  `InstalledModel` row surviving after its files were pruned from `/models`) surfaces as a pod-level
  `FileNotFoundError`, not a friendlier pre-flight UI error.
- The pre-existing `InstalledModelResponse` bug (its `to_dict()`-sourced `"input"` key doesn't match the
  schema's `input_modalities` field; `kind` isn't declared on the schema at all, so both are silently dropped
  from any `to_dict()`-based response) is unrelated to this change and was left as-is — the new picker only
  needs `friendly_name`/`task_ids`, both of which round-trip correctly today.
