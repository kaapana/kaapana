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
            # DAG and this DAG never needs the /models lookup that branch guards.
            pc_models.BaseEnv(name="WORKFLOW_NAME", value="classification-training"),
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

    training = KaapanaTaskOperator(
        task_id="training",
        image=f"{DEFAULT_REGISTRY}/classification-training:{KAAPANA_BUILD_VERSION}",
        taskTemplate="train",
        env=[
            pc_models.BaseEnv(name="TAG_TO_CLASS_MAPPING_JSON", value="tag1,tag2"),
            pc_models.BaseEnv(name="TASK", value="binary"),
            pc_models.BaseEnv(name="DIMENSIONS", value="3D"),
            pc_models.BaseEnv(name="PATCH_SIZE", value="(128, 128, 128)"),
            pc_models.BaseEnv(name="BATCH_SIZE", value="1"),
            pc_models.BaseEnv(name="NUM_EPOCHS", value="1600"),
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

    persist_model = KaapanaTaskOperator(
        task_id="persist-model",
        image=f"{DEFAULT_REGISTRY}/persist-model:{KAAPANA_BUILD_VERSION}",
        taskTemplate="persist",
        env=[
            # DAG_ID is statically known and not injected by KaapanaTaskOperator (see
            # migration-notes.md) — the subdirectory of the shared /models volume this
            # DAG's checkpoints are persisted under.
            pc_models.BaseEnv(name="DAG_ID", value="classification-training"),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=training,
                upstream_output_channel="model",
                input_channel="model",
            )
        ],
    )


download >> convert >> preprocessing >> training >> persist_model
