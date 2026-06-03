"""Demo fine-tune DAG on the Task API path — now self-bootstrapping + write-back.

Each input channel is a Data API *query* (see workflow.json). The frontend
resolves the user's selection to a fixed list of entity IDs and submits it; that
list travels to the matching download task as the ``INPUT_ENTITY_IDS`` env var —
so each ``task_id`` here MUST match a ``task_title`` in workflow.json:
``download_segmentations`` and ``download_model``. workflow-api never contacts the
Data API.

Because the IDs are client-supplied, each download task is also given its
channel's designer ``constraint_query`` as ``INPUT_CONSTRAINT_QUERY`` (mirrors
workflow.json) and its ``INPUT_CARDINALITY``; the operator validates every
supplied ID against the constraint and the cardinality, failing the task on a
violation — re-establishing the guarantee server-side-of-the-pod.

The model channel is OPTIONAL and single-cardinality: leave it empty to train the
first model from scratch (the download task then no-ops to an empty channel). The
dummy training task receives both channels via IOMapping, proves they arrived,
and emits a dummy model + an ``upload_manifest.json``. The new ``upload_model``
task writes that model back via the storage-api (bytes → S3) and registers a new
Data API entity carrying ``model-card`` + ``provenance`` metadata — so a later
run can select it (the model constraint scopes to this workflow's provenance).

The ``ensure_schema`` root task ensures this workflow's *own* metadata key
(``finetune-note``) is registered on the Data API before the write-back attaches
it — the worked example of a workflow adding a workflow-specific key itself,
rather than relying on the workflow-installer. (The platform-shipped keys
``model-card`` + ``provenance`` need no such task; they ship via a data-api
migration.)
"""

import json

from airflow.models import DAG
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from task_api_operators.KaapanaTaskOperator import IOMapping, KaapanaTaskOperator

args = {
    "ui_visible": True,
    "owner": "kaapana",
}

# Designer constraints, kept in sync with workflow.json's ui_form.constraint_query.
# Shipped to the operator so it can re-validate the client-supplied entity IDs.
SEG_CONSTRAINT = {
    "type": "filter",
    "field": "metadata.dicom-series.00080060 Modality_keyword",
    "op": "eq",
    "value": "SEG",
}
# Only models produced by THIS workflow are selectable (discovery convention, not
# an enforced guarantee — provenance is forgeable until the privilege gate lands).
MODEL_CARD_CONSTRAINT = {
    "type": "group",
    "op": "and",
    "children": [
        {"type": "filter", "field": "metadata.model-card", "op": "has_key"},
        {
            "type": "filter",
            "field": "metadata.provenance.workflow_name",
            "op": "starts_with",
            "value": "data-api-finetune-demo",
        },
    ],
}


with DAG("{{ dag_id }}", default_args=args) as dag:
    ensure_schema = KaapanaTaskOperator(
        task_id="ensure_schema",
        image=f"{DEFAULT_REGISTRY}/data-api-ensure-schema:{KAAPANA_BUILD_VERSION}",
        taskTemplate="data-api-ensure-schema",
        env=[],
    )

    download_segmentations = KaapanaTaskOperator(
        task_id="download_segmentations",
        image=f"{DEFAULT_REGISTRY}/data-api-download:{KAAPANA_BUILD_VERSION}",
        taskTemplate="data-api-download",
        env=[
            {"name": "INPUT_CONSTRAINT_QUERY", "value": json.dumps(SEG_CONSTRAINT)},
            {"name": "INPUT_CARDINALITY", "value": "multiple"},
        ],
    )

    download_model = KaapanaTaskOperator(
        task_id="download_model",
        image=f"{DEFAULT_REGISTRY}/data-api-download:{KAAPANA_BUILD_VERSION}",
        taskTemplate="data-api-download",
        env=[
            {
                "name": "INPUT_CONSTRAINT_QUERY",
                "value": json.dumps(MODEL_CARD_CONSTRAINT),
            },
            {"name": "INPUT_CARDINALITY", "value": "single"},
        ],
    )

    finetune = KaapanaTaskOperator(
        task_id="finetune",
        image=f"{DEFAULT_REGISTRY}/data-api-finetune-train:{KAAPANA_BUILD_VERSION}",
        taskTemplate="data-api-finetune-train",
        env=[],
        iochannel_maps=[
            IOMapping(
                upstream_operator=download_segmentations,
                upstream_output_channel="downloads",
                input_channel="segmentations",
            ),
            IOMapping(
                upstream_operator=download_model,
                upstream_output_channel="downloads",
                input_channel="model",
            ),
        ],
    )

    upload_model = KaapanaTaskOperator(
        task_id="upload_model",
        image=f"{DEFAULT_REGISTRY}/data-api-upload:{KAAPANA_BUILD_VERSION}",
        taskTemplate="data-api-upload",
        env=[],
        iochannel_maps=[
            IOMapping(
                upstream_operator=finetune,
                upstream_output_channel="trained-model",
                input_channel="results",
            ),
        ],
    )


download_segmentations >> finetune

download_model >> finetune

finetune >> upload_model

ensure_schema >> upload_model
