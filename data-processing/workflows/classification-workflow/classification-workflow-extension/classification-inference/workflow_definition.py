from airflow.models import DAG
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from task_api.processing_container import pc_models
from task_api_operators.KaapanaTaskOperator import IOMapping, KaapanaTaskOperator

args = {
    "ui_visible": True,
    "owner": "kaapana",
}


with DAG("{{ dag_id }}", default_args=args) as dag:
    download = KaapanaTaskOperator(
        task_id="download",
        image=f"{DEFAULT_REGISTRY}/get-input-task:{KAAPANA_BUILD_VERSION}",
        taskTemplate="dicom-download",
    )

    convert = KaapanaTaskOperator(
        task_id="convert",
        image=f"{DEFAULT_REGISTRY}/mitk-tools:{KAAPANA_BUILD_VERSION}",
        taskTemplate="convert",
        iochannel_maps=[
            IOMapping(
                upstream_operator=download,
                upstream_output_channel="downloads",
                input_channel="dicom",
            )
        ],
    )

    preprocessing = KaapanaTaskOperator(
        task_id="preprocessing",
        image=f"{DEFAULT_REGISTRY}/classification-preprocessing:{KAAPANA_BUILD_VERSION}",
        taskTemplate="preprocess",
        env=[
            pc_models.BaseEnv(name="PATCH_SIZE", value="(128, 128, 128)"),
            # WORKFLOW_NAME is read by the container's untouched inference-only branch
            # (see migration-notes.md); hardcoded here since it's statically known per
            # DAG. TASK_IDS (also read by that branch) has no sensible static default —
            # it's supplied per-run via the "TASK_IDS" workflow_parameter instead.
            pc_models.BaseEnv(name="WORKFLOW_NAME", value="classification-inference"),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=convert,
                upstream_output_channel="nrrd",
                input_channel="nrrd",
            )
        ],
        labels={"network-access-opensearch": "true"},
    )

    inference = KaapanaTaskOperator(
        task_id="inference",
        image=f"{DEFAULT_REGISTRY}/classification-inference:{KAAPANA_BUILD_VERSION}",
        taskTemplate="infer",
        env=[
            pc_models.BaseEnv(name="TAG_POSTFIX", value="False"),
            # DAG_ID is statically known and not injected by KaapanaTaskOperator (see
            # migration-notes.md) — hardcoded here so the container's untouched
            # /models/<DAG_ID>/... path construction resolves correctly. TASK_IDS and
            # RUN_ID have no sensible static default and are supplied per-run via
            # workflow_parameters instead.
            pc_models.BaseEnv(name="DAG_ID", value="classification-inference"),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=preprocessing,
                upstream_output_channel="preprocessed",
                input_channel="preprocessed",
            )
        ],
        labels={"network-access-opensearch": "true"},
    )


download >> convert >> preprocessing >> inference
