import glob
import json
import os
from datetime import timedelta
from pathlib import Path

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.exceptions import AirflowSkipException

from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.MinioOperator import MinioOperator
from kaapana.operators.Json2MetaOperator import Json2MetaOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

from trident_ops.TridentPatchingOperator import TridentPatchingOperator
from trident_ops.TridentFeatureExtractionOperator import TridentFeatureExtractionOperator
from trident_ops.EncapsulateFeaturesDicomOperator import EncapsulateFeaturesDicomOperator

"""
DAG B of the TRIDENT WSI integration (see DAG A: trident-tissue-segmentation).

At trigger time, select the WSI series itself (the same series you ran DAG A
on). The matching tissue-mask GeoJSON is pulled directly from MinIO, keyed by
series UID alone (trident-segmentations/<series-uid>.geojson) - DAG A's own
real persistence target, independent of any DICOM round-trip. There is
currently no correct-and-write-back loop: this uses the segmentation as
TRIDENT produced it (an earlier design based on a DICOM Parametric Map the
user could correct in SLIM was dropped - it OOM-killed on real-sized WSIs,
and the SLIM<->PACS write-back path it depended on was not confirmed working
in this deployment anyway).

Pipeline: pull the WSI + its GeoJSON mask from MinIO -> TRIDENT patch-
coordinate extraction restricted to that mask -> TRIDENT foundation-model
feature extraction -> branch on `output_target`: encapsulate+send to PACS,
or push the raw h5 to MinIO (+ OpenSearch link via Json2MetaOperator).
"""

MINIO_PREFIX = "trident-segmentations"

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "patch_encoder": {
                "title": "Foundation model",
                "description": "Any key from trident.patch_encoder_models.load.encoder_registry, "
                "e.g. uni_v1, uni_v2, conch_v15, gigapath, virchow2, phikon_v2, hoptimus1, ...",
                "type": "string",
                "default": "uni_v2",
            },
            "hf_token": {
                "title": "HuggingFace token",
                "description": "Your own HuggingFace access token, needed to download gated model "
                "weights (UNI, UNI2-h, CONCH, Virchow, ...). Leave empty if the chosen model's "
                "weights were baked into the trident image/volume already.",
                "type": "string",
                "default": "",
            },
            "target_magnification": {
                "title": "Patch magnification",
                "type": "integer",
                "default": 20,
            },
            "patch_size": {
                "title": "Patch size (px)",
                "type": "integer",
                "default": 256,
            },
            "overlap": {
                "title": "Patch overlap (px)",
                "type": "integer",
                "default": 0,
            },
            "min_tissue_proportion": {
                "title": "Minimum tissue proportion",
                "description": "Minimum tissue-overlap fraction (0-1) for a patch to be kept.",
                "type": "number",
                "default": 0.0,
            },
            "batch_limit": {
                "title": "Inference batch size",
                "type": "integer",
                "default": 64,
            },
            "output_target": {
                "title": "Output destination",
                "description": "Where the extracted features should land.",
                "type": "string",
                "enum": ["pacs", "minio"],
                "default": "pacs",
            },
        },
        "required": ["patch_encoder", "output_target"],
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
    dag_id="trident-feature-extraction",
    default_args=args,
    concurrency=5,
    max_active_runs=3,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag, data_type="all", check_modality=False)


def pull_geojson_from_minio_callback(ds, **kwargs):
    """
    Downloads the tissue-mask GeoJSON for each selected WSI series from MinIO,
    using the series UID alone as the lookup key - the exact counterpart of
    DAG A's push_geojson_to_minio_callback.
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
        out_dir = Path(batch_element_dir) / pull_geojson.operator_out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        object_name = f"{MINIO_PREFIX}/{series_uid}.geojson"
        dest_path = out_dir / f"{series_uid}.geojson"
        try:
            client.fget_object(bucket_name, object_name, str(dest_path))
            print(f"Downloaded s3://{bucket_name}/{object_name} -> {dest_path}")
        except Exception as e:
            print(
                f"No segmentation found at s3://{bucket_name}/{object_name} ({e}) "
                f"- run trident-tissue-segmentation on this series first. Skipping {batch_element_dir}."
            )


pull_geojson = KaapanaPythonBaseOperator(
    dag=dag,
    name="pull-geojson-from-minio",
    python_callable=pull_geojson_from_minio_callback,
    input_operator=get_input,
)

patching = TridentPatchingOperator(
    dag=dag,
    dicom_operator=get_input,
    geojson_operator=pull_geojson,
)

feat = TridentFeatureExtractionOperator(
    dag=dag,
    dicom_operator=get_input,
    coords_operator=patching,
)


def check_output_target_callback(ds, **kwargs):
    target = kwargs["params"]["target"]
    conf = kwargs["dag_run"].conf
    output_target = (conf.get("workflow_form", {}) or {}).get("output_target", "pacs")
    if output_target != target:
        raise AirflowSkipException(f"output_target={output_target!r} != {target!r} - skipping")


check_pacs = KaapanaPythonBaseOperator(
    dag=dag,
    name="check-output-target-pacs",
    python_callable=check_output_target_callback,
    params={"target": "pacs"},
)

check_minio = KaapanaPythonBaseOperator(
    dag=dag,
    name="check-output-target-minio",
    python_callable=check_output_target_callback,
    params={"target": "minio"},
)

encapsulate = EncapsulateFeaturesDicomOperator(
    dag=dag,
    dicom_operator=get_input,
    features_operator=feat,
)

dcm_send = DcmSendOperator(dag=dag, input_operator=encapsulate)

put_minio = MinioOperator(
    dag=dag,
    action="put",
    minio_prefix="trident-features",
    batch_input_operators=[feat],
    whitelisted_file_extensions=[".h5"],
)


def write_minio_link_json_callback(ds, **kwargs):
    batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME
    conf = kwargs["dag_run"].conf
    patch_encoder = (conf.get("workflow_form", {}) or {}).get("patch_encoder", "uni_v2")

    for batch_element_dir in glob.glob(os.path.join(batch_dir, "*")):
        features_dir = Path(batch_element_dir) / feat.operator_out_dir
        feature_files = glob.glob(str(features_dir / "**" / "*.h5"), recursive=True)
        if not feature_files:
            continue

        out_dir = Path(batch_element_dir) / write_minio_link_json.operator_out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        relative_path = os.path.relpath(feature_files[0], str(Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id))
        # Field names prefixed trident_ AND deliberately avoiding the substring
        # "_object" anywhere in the name: Kaapana's own OpenSearch index template
        # (services/meta/meta-init/docker/files/start.py) defines a dynamic_templates
        # rule that maps ANY field matching regex "^.*_object.*$" to an "object"
        # type - "minio_object_path" (and even the already-renamed
        # "trident_minio_object_path") matched it, so a plain string push always
        # failed with a mapper_parsing_exception regardless of any actual name
        # collision. This isn't specific to our field - it's a reserved,
        # platform-wide naming pattern, so just avoid "_object" entirely.
        link = {
            "trident_minio_prefix": "trident-features",
            "trident_minio_path": relative_path,
            "trident_patch_encoder": patch_encoder,
        }
        (out_dir / "minio_link.json").write_text(json.dumps(link, indent=2))


write_minio_link_json = KaapanaPythonBaseOperator(
    dag=dag,
    name="write-minio-link-json",
    python_callable=write_minio_link_json_callback,
    input_operator=feat,
)

json2meta = Json2MetaOperator(
    dag=dag,
    dicom_operator=get_input,
    json_operator=write_minio_link_json,
)

clean = LocalWorkflowCleanerOperator(
    dag=dag, clean_workflow_dir=True, trigger_rule="none_failed"
)

(
    get_input
    >> pull_geojson
    >> patching
    >> feat
    >> check_pacs
    >> encapsulate
    >> dcm_send
    >> clean
)
feat >> check_minio >> put_minio >> write_minio_link_json >> json2meta >> clean
