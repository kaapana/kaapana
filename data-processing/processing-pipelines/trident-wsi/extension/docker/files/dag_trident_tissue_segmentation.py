import glob
import os
from datetime import timedelta
from pathlib import Path

from airflow.models import DAG
from airflow.utils.dates import days_ago

from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

from trident_ops.TridentSegmentationOperator import TridentSegmentationOperator
from trident_ops.GeojsonToSROperator import GeojsonToSROperator

"""
DAG A of the TRIDENT WSI integration (see DAG B: trident-feature-extraction).

Pipeline: select a DICOM WSI series -> TRIDENT tissue segmentation -> the raw
GeoJSON mask is pushed straight to MinIO, keyed by the series UID - this is
the actual persistent handoff to DAG B, a deliberately simple, rasterization-
free design (an earlier DICOM Parametric Map approach OOM-killed on
real-sized WSIs regardless of how conservatively its working resolution was
capped). In parallel, a lightweight DICOM Comprehensive 3D SR (vector
SCOORD3D regions, not a rasterized image) is also sent to PACS purely so the
result can be inspected in SLIM - this SR is QC/visualization only, nothing
downstream reads it back. There is currently no correct-and-write-back loop:
DAG B uses the segmentation as TRIDENT produced it.
"""

MINIO_PREFIX = "trident-segmentations"

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "segmenter_model": {
                "title": "Segmentation model",
                "description": "TRIDENT tissue-segmentation model to use.",
                "type": "string",
                "enum": ["hest", "grandqc"],
                "default": "hest",
            },
            "seg_mag": {
                "title": "Segmentation magnification",
                "description": "Magnification TRIDENT segments tissue at.",
                "type": "integer",
                "default": 10,
            },
            "confidence_thresh": {
                "title": "Confidence threshold",
                "description": "Softmax confidence threshold for the binary tissue mask.",
                "type": "number",
                "default": 0.5,
            },
            "holes_are_tissue": {
                "title": "Treat holes as tissue",
                "description": "If true, gaps/background enclosed within the outer tissue "
                "boundary are filled in as tissue too - this merges separate nearby tissue "
                "fragments (and any background between them) into one contour. Leave off to "
                "get a contour that actually follows each piece of tissue.",
                "type": "boolean",
                "default": False,
            },
        },
        "required": ["segmenter_model", "seg_mag"],
    },
}

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=60),
}

dag = DAG(
    dag_id="trident-tissue-segmentation",
    default_args=args,
    concurrency=5,
    max_active_runs=3,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag, data_type="all", check_modality=False)

segment = TridentSegmentationOperator(dag=dag, dicom_operator=get_input)


def push_geojson_to_minio_callback(ds, **kwargs):
    """
    Uploads the GeoJSON tissue mask to MinIO at a deterministic key based on
    the series UID alone (trident-segmentations/<series-uid>.geojson) - this
    is DAG B's actual lookup key, independent of which DAG A run produced it
    or any Kaapana-internal workflow/run-id path, so DAG B (triggered
    separately, potentially much later) can find it from the series UID alone.
    """
    from kaapanapy.helper.HelperMinioSessionManager import HelperMinioSessionManager

    conf = kwargs["dag_run"].conf
    bucket_name = (conf.get("project_form", {}) or {}).get("s3_bucket")
    if not bucket_name:
        raise ValueError("Could not determine the project's MinIO bucket from dag_run.conf['project_form']")

    client = HelperMinioSessionManager().get_client()

    batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME
    for batch_element_dir in glob.glob(os.path.join(batch_dir, "*")):
        series_uid = os.path.basename(batch_element_dir)
        geojson_dir = Path(batch_element_dir) / segment.operator_out_dir
        geojson_files = glob.glob(str(geojson_dir / "**" / "*.geojson"), recursive=True)
        if not geojson_files:
            print(f"No GeoJSON found under {geojson_dir} - skipping {batch_element_dir}")
            continue

        object_name = f"{MINIO_PREFIX}/{series_uid}.geojson"
        client.fput_object(bucket_name, object_name, geojson_files[0])
        print(f"Uploaded {geojson_files[0]} -> s3://{bucket_name}/{object_name}")


push_geojson_to_minio = KaapanaPythonBaseOperator(
    dag=dag,
    name="push-geojson-to-minio",
    python_callable=push_geojson_to_minio_callback,
    input_operator=segment,
)

to_sr = GeojsonToSROperator(
    dag=dag,
    dicom_operator=get_input,
    segmentation_operator=segment,
)

dcm_send = DcmSendOperator(dag=dag, input_operator=to_sr)

clean = LocalWorkflowCleanerOperator(
    dag=dag, clean_workflow_dir=True, trigger_rule="none_failed"
)

get_input >> segment >> push_geojson_to_minio >> clean
segment >> to_sr >> dcm_send >> clean
