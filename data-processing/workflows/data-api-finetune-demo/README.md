# Data API Fine-tune Demo

A **demo** workflow on the new Task API path that proves the query-constrained
input pipeline **and** the write-back pipeline end to end. It does no real
training — its job is to show that Data API *query* channels are resolved to a
fixed entity set, materialised on disk by a store-agnostic download task, handed
to a downstream task via IOMapping, and that the produced result is written back
to a store + registered as a new Data API entity with provenance.

> Do not model production workflows on the training step here — it is deliberately
> a no-op. Only the **plumbing** (query channels → client-resolved IDs →
> storage-api download → IOMapping → storage-api upload → new entity) is the
> pattern to reuse.

It is **self-bootstrapping**: the base-model channel is optional, so the first
run trains from scratch and produces the first model; later runs select it.

## Channels

| Channel (`task_id` = `task_title`) | Cardinality | Constraint query | Notes |
|---|---|---|---|
| `download_segmentations` | multiple | `metadata.dicom-series.00080060 Modality_keyword` `eq` `"SEG"` | User may narrow further or pick an existing dataset (`allow_existing_dataset: true`). |
| `download_model` | single (optional) | `has_key metadata.model-card` **AND** `metadata.provenance.workflow_name starts_with "data-api-finetune-demo"` | Single-select; leave empty on the first run to train from scratch. Scoped to models **this workflow** produced. |

> ⚠️ **Provenance scoping is a discovery convention, not an enforced guarantee.**
> The model constraint scopes selectable models to `provenance.workflow_name`, but
> `provenance` is a normal metadata key any writer could set — the privileged-key
> gate that would make it authoritative is deferred (see repo-root `DATA_API.md`).

> ⚠️ **Verify the segmentation field path against ingested SEG data.** If it
> doesn't match your stored `dicom-series` documents the channel resolves to an
> empty set and submit is blocked. Adjust the constraint in
> `workflow-chart/files/workflow.json` **and** the matching `*_CONSTRAINT` in
> `dag_data_api_finetune_demo.py`.

## How it works

**Input (workflow-api is Data-API-agnostic):**

1. `workflow.json` declares each channel as `ui_form.type: "query"` with a
   designer-fixed `constraint_query` and a `cardinality`. Each `task_title` is
   byte-identical to a DAG `task_id`.
2. The workflow-ui lets the user narrow within the constraint and preview matches
   (single-cardinality channels render a single-select). **At submit it resolves
   the selection to an entity-ID list** and submits it as the channel parameter's
   value — workflow-api forwards it like any parameter and **never contacts the
   Data API**.
3. The Airflow adapter injects the list as `INPUT_ENTITY_IDS` on the matching
   `task_title`.
4. The DAG ships each channel's `constraint_query` (`INPUT_CONSTRAINT_QUERY`) and
   `INPUT_CARDINALITY`. `data-api-download` **re-validates** every supplied ID
   against the constraint and the cardinality, then resolves IDs → storage
   coordinates → streams bytes via the storage-api into its `downloads` channel as
   `<entity_id>/<files>`. An empty model selection no-ops to an empty channel.
5. IOMapping hands both channels to `finetune`, which lists what arrived and emits
   a dummy model + an `upload_manifest.json` (declares the `model-card` to attach
   and the upstream entity IDs for lineage).

**Write-back:**

6. `upload_model` (`data-api-upload`) reads the produced files + manifest, uploads
   the bytes via the storage-api (model files → S3; DICOM would STOW-RS to PACS),
   mints a new Data API entity with the returned coordinates, and attaches
   `model-card` + `finetune-note` (from the manifest) + `provenance` (stamped from
   the run-context env the KaapanaTaskOperator injects — `KAAPANA_WORKFLOW_RUN_ID` /
   `DAG_ID` / `TASK_ID` / `IMAGE` — so the producing task can't forge it).

**Schema ownership:**

The Data API rejects a metadata POST whose key has no registered schema.

- `model-card` and `provenance` are **platform-shipped** keys (registered by a
  data-api alembic migration), present on every install — no per-workflow step.
- `finetune-note` is this workflow's **own** key. The `ensure_schema` root task
  (`data-api-ensure-schema`) registers it at run time (idempotent) before the
  write-back attaches it. This is the worked example of how a workflow adds a
  workflow-specific Data API key itself — the **workflow-installer never contacts
  the Data API**.

## Test-data prep (run once, before the first run)

No schema registration step is needed: `model-card` + `provenance` are
platform-shipped (data-api migration), and `finetune-note` is registered by the
DAG's own `ensure_schema` task on each run.

1. **Ingest a few DICOM-SEG series** (the standard ingest path) so the
   segmentation channel has matches.
2. **Create the first run** with **no** base model selected → trains from scratch,
   writes back the first model entity.
3. **Create a second run**: the base-model single-select now offers that model;
   provenance lineage chains across runs.

> No base-model entity needs pre-seeding — the first run produces it.
