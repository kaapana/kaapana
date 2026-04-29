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


with DAG("{{ dag_id }}", default_args=args) as dag:
    wsi_fetcher = KaapanaTaskOperator(
        task_id="wsi-fetcher",
        image=f"{DEFAULT_REGISTRY}/wsi-fetcher:{KAAPANA_BUILD_VERSION}",
        taskTemplate="wsi-fetcher",
    )

    svs_to_dicom = KaapanaTaskOperator(
        task_id="svs-to-dicom",
        image=f"{DEFAULT_REGISTRY}/svs-to-dicom:{KAAPANA_BUILD_VERSION}",
        taskTemplate="svs-to-dicom",
        iochannel_maps=[
            IOMapping(
                upstream_operator=wsi_fetcher,
                upstream_output_channel="wsi",
                input_channel="wsi",
            )
        ],
    )

    slide_label_remover_dummy = KaapanaTaskOperator(
        task_id="slide-label-remover-dummy",
        image=f"{DEFAULT_REGISTRY}/slide-label-remover-dummy:{KAAPANA_BUILD_VERSION}",
        taskTemplate="slide-label-remover-dummy",
        iochannel_maps=[
            IOMapping(
                upstream_operator=svs_to_dicom,
                upstream_output_channel="dicom",
                input_channel="dicom",
            )
        ],
    )

    dicom_pseudonymizer = KaapanaTaskOperator(
        task_id="dicom-pseudonymizer",
        image=f"{DEFAULT_REGISTRY}/dicom-pseudonymizer:{KAAPANA_BUILD_VERSION}",
        taskTemplate="dicom-pseudonymizer",
        iochannel_maps=[
            IOMapping(
                upstream_operator=slide_label_remover_dummy,
                upstream_output_channel="dicom-label-removed",
                input_channel="dicom-label-removed",
            )
        ],
    )

    dsf_exporter = KaapanaTaskOperator(
        task_id="dsf-exporter",
        image=f"{DEFAULT_REGISTRY}/dsf-exporter:{KAAPANA_BUILD_VERSION}",
        taskTemplate="dsf-exporter",
        iochannel_maps=[
            IOMapping(
                upstream_operator=dicom_pseudonymizer,
                upstream_output_channel="dicom-psn",
                input_channel="dicom-psn",
            )
        ],
    )

    (
        wsi_fetcher
        >> svs_to_dicom
        >> slide_label_remover_dummy
        >> dicom_pseudonymizer
        >> dsf_exporter
    )
