from airflow.models import DAG
from task_api_operators.KaapanaTaskOperator import KaapanaTaskOperator, IOMapping
from task_api.processing_container import pc_models

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


args = {
    "ui_visible": True,
    "owner": "kaapana",
}


with DAG("register-dicoms", default_args=args) as dag:
    download_registration_target = KaapanaTaskOperator(
        task_id="download_registration_target",
        image=f"{DEFAULT_REGISTRY}/get-input-task:{KAAPANA_BUILD_VERSION}",
        taskTemplate="dicom-download",
        env=[
            pc_models.BaseEnv(name="DATASET", value="FIXED"),
            pc_models.BaseEnv(
                name="KAAPANA_PROJECT_IDENTIFIER",
                value="cd98d3b5-6e15-44d9-80d8-53bc8523d063",
            ),
        ],
    )

    download_moving_images = KaapanaTaskOperator(
        task_id="download_moving_images",
        image=f"{DEFAULT_REGISTRY}/get-input-task:{KAAPANA_BUILD_VERSION}",
        taskTemplate="dicom-download",
        env=[
            pc_models.BaseEnv(name="DATASET", value="MOVING"),
            pc_models.BaseEnv(
                name="KAAPANA_PROJECT_IDENTIFIER",
                value="cd98d3b5-6e15-44d9-80d8-53bc8523d063",
            ),
        ],
    )

    convert_target_to_nrrd = KaapanaTaskOperator(
        task_id="convert_target_to_nrrd",
        image=f"{DEFAULT_REGISTRY}/mitk-tools:{KAAPANA_BUILD_VERSION}",
        taskTemplate="convert",
        env=[],
        iochannel_maps=[
            IOMapping(
                upstream_operator=download_registration_target,
                upstream_output_channel="downloads",
                input_channel="dicom",
            )
        ],
    )

    convert_moving_images_to_nrrd = KaapanaTaskOperator(
        task_id="convert_moving_images_to_nrrd",
        image=f"{DEFAULT_REGISTRY}/mitk-tools:{KAAPANA_BUILD_VERSION}",
        taskTemplate="convert",
        env=[],
        iochannel_maps=[
            IOMapping(
                upstream_operator=download_moving_images,
                upstream_output_channel="downloads",
                input_channel="dicom",
            )
        ],
    )

    register_images = KaapanaTaskOperator(
        task_id="register_images",
        image=f"{DEFAULT_REGISTRY}/mitk-tools:{KAAPANA_BUILD_VERSION}",
        taskTemplate="register",
        env=[],
        iochannel_maps=[
            IOMapping(
                upstream_operator=convert_target_to_nrrd,
                upstream_output_channel="nrrd",
                input_channel="fixed",
            ),
            IOMapping(
                upstream_operator=convert_moving_images_to_nrrd,
                upstream_output_channel="nrrd",
                input_channel="moving",
            ),
        ],
    )

    convert_registered_nrrd_to_dicom = KaapanaTaskOperator(
        task_id="convert_registered_nrrd_to_dicom",
        image=f"{DEFAULT_REGISTRY}/nrrd-to-dicom:{KAAPANA_BUILD_VERSION}",
        taskTemplate="nrrd-to-dicom",
        env=[],
        iochannel_maps=[
            IOMapping(
                upstream_operator=register_images,
                upstream_output_channel="registered",
                input_channel="nrrd",
            ),
            IOMapping(
                upstream_operator=download_moving_images,
                upstream_output_channel="downloads",
                input_channel="reference",
            ),
        ],
    )

    send_registered_dicoms = KaapanaTaskOperator(
        task_id="send_registered_dicoms",
        image=f"{DEFAULT_REGISTRY}/send-dicoms:{KAAPANA_BUILD_VERSION}",
        taskTemplate="send-dicoms",
        env=[
            pc_models.BaseEnv(name="DATASET", value="REGISTERED"),
            pc_models.BaseEnv(name="PROJECT_NAME", value="admin"),
            pc_models.BaseEnv(name="PACS_HOST", value="ctp-dicom-service.services.svc"),
            pc_models.BaseEnv(name="PACS_PORT", value="11112"),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=convert_registered_nrrd_to_dicom,
                upstream_output_channel="dicom",
                input_channel="dicoms",
            )
        ],
        labels={"network-access-ctp": "true"},
    )


download_registration_target >> convert_target_to_nrrd >> register_images

download_moving_images >> convert_moving_images_to_nrrd >> register_images

register_images >> convert_registered_nrrd_to_dicom >> send_registered_dicoms
