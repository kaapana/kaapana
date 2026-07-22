from datetime import timedelta

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
    "retries": 0,
}


with DAG("{{ dag_id }}", default_args=args) as dag:
    download_dataset = KaapanaTaskOperator(
        task_id="download_dataset",
        image=f"{DEFAULT_REGISTRY}/get-input-task:{KAAPANA_BUILD_VERSION}",
        taskTemplate="dicom-download",
        execution_timeout=timedelta(hours=6),
    )

    convert_to_nrrd = KaapanaTaskOperator(
        task_id="convert_to_nrrd",
        image=f"{DEFAULT_REGISTRY}/mitk-tools:{KAAPANA_BUILD_VERSION}",
        taskTemplate="convert",
        execution_timeout=timedelta(hours=6),
        iochannel_maps=[
            IOMapping(
                upstream_operator=download_dataset,
                upstream_output_channel="downloads",
                input_channel="dicom",
            )
        ],
    )

    localize_head = KaapanaTaskOperator(
        task_id="localize_head",
        image=f"{DEFAULT_REGISTRY}/bodypartregression-task-api:{KAAPANA_BUILD_VERSION}",
        taskTemplate="predict-body-parts",
        execution_timeout=timedelta(hours=6),
        retries=2,
        iochannel_maps=[
            IOMapping(
                upstream_operator=convert_to_nrrd,
                upstream_output_channel="nrrd",
                input_channel="nrrd",
            )
        ],
    )

    # ###########################
    # Exercise: connect head-demo-tools to the workflow.
    #
    # Consume "nrrd" from convert_to_nrrd and "bpr-json"
    # from localize_head. Produce the "nrrd" used by the next task.
    # ###########################

    replace_head = KaapanaTaskOperator(
        task_id="TODO",
        image=f"{DEFAULT_REGISTRY}/TODO:{KAAPANA_BUILD_VERSION}",
        taskTemplate="TODO",
        execution_timeout=timedelta(hours=2),
        iochannel_maps=[
            IOMapping(
                upstream_operator=TODO,
                upstream_output_channel="TODO",
                input_channel="TODO",
            ),
            IOMapping(
                upstream_operator=TODO,
                upstream_output_channel="TODO",
                input_channel="TODO",
            ),
        ],
    )

    # ###########################
    # End exercise
    # ###########################

    convert_to_derived_dicom = KaapanaTaskOperator(
        task_id="convert_to_derived_dicom",
        image=f"{DEFAULT_REGISTRY}/nrrd-to-dicom:{KAAPANA_BUILD_VERSION}",
        taskTemplate="nrrd-to-dicom",
        execution_timeout=timedelta(hours=6),
        iochannel_maps=[
            IOMapping(
                upstream_operator=replace_head,
                upstream_output_channel="nrrd",
                input_channel="nrrd",
            ),
            IOMapping(
                upstream_operator=download_dataset,
                upstream_output_channel="downloads",
                input_channel="reference",
            ),
        ],
    )

    send_derived_dicoms = KaapanaTaskOperator(
        task_id="send_derived_dicoms",
        image=f"{DEFAULT_REGISTRY}/send-dicoms:{KAAPANA_BUILD_VERSION}",
        taskTemplate="send-dicoms",
        execution_timeout=timedelta(hours=1),
        retries=2,
        env=[
            pc_models.BaseEnv(name="DATASET", value="head-sphere"),
            pc_models.BaseEnv(name="PROJECT_NAME", value="admin"),
            pc_models.BaseEnv(
                name="PACS_HOST", value="ctp-dicom-service.services.svc"
            ),
            pc_models.BaseEnv(name="PACS_PORT", value="11112"),
        ],
        labels={"network-access-ctp": "true"},
        iochannel_maps=[
            IOMapping(
                upstream_operator=convert_to_derived_dicom,
                upstream_output_channel="dicom",
                input_channel="dicoms",
            )
        ],
    )

    (
        download_dataset
        >> convert_to_nrrd
        >> localize_head
        >> replace_head
        >> convert_to_derived_dicom
        >> send_derived_dicoms
    )
