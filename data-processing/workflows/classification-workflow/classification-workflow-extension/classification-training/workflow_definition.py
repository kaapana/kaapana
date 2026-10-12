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
            # The preprocessing container is shared by both DAGs. WORKFLOW_NAME tells it whether to read the
            # patch size from the selected model.
            pc_models.BaseEnv(name="WORKFLOW_NAME", value="classification-training"),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=convert,
                upstream_output_channel="nrrd",
                input_channel="nrrd",
            )
        ],
    )

    training = KaapanaTaskOperator(
        task_id="training",
        image=f"{DEFAULT_REGISTRY}/classification-training:{KAAPANA_BUILD_VERSION}",
        taskTemplate="train",
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
            # The Task API does not provide the DAG ID to the task. persist-model uses it as the model directory.
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
