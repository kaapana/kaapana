import glob
import logging
import os
from datetime import timedelta
from pathlib import Path

import pydicom
from pydicom.uid import generate_uid
from airflow.models import DAG
from airflow.utils.dates import days_ago

from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from autosegmentationpipeline.BodyPartInferenceOperator import BODY_PART_TO_CANONICAL
from autosegmentationpipeline.DynamicConfDagTriggerOperator import (
    DynamicConfDagTriggerOperator,
)

"""
Takes exactly two manually-selected series (one radiology CT/MR, one pathology
SM/WSI - selected via Kaapana's own dataset-browser checkbox multi-select,
same as any other DAG triggered from there) whose radiology<->pathology
association has been lost (different PatientID due to pseudonymization or
different DICOM conversion pipelines, and/or the pathology slide lacking a
recognizable body-part tag), and repairs it at the actual DICOM-tag level:
  1. resolves which of the two is which by DICOM modality (order-independent)
  2. rewrites the pathology series' own DICOM files: PatientID set to match
     the radiology series' PatientID, BodyPartExamined forced if the user
     supplied a body part override (for slides that don't carry one), and
     fresh StudyInstanceUID/SeriesInstanceUID/SOPInstanceUIDs generated (see
     note below on why this is required, not optional)
  3. re-sends the retagged pathology files into the PACS, so Kaapana's normal
     ingestion re-indexes them under the corrected tags
  4. deletes the old, wrongly-tagged pathology series from the PACS, now that
     the corrected copy is safely stored under its own, unrelated UIDs

Fresh UIDs in step 2 are required, not a style choice: Kaapana's own stock
ingestion (service-process-incoming-dcm, triggered automatically by CTP for
*any* DICOM arriving via AE-title routing - nothing specific to this DAG)
re-submits every newly-arrived instance into dicom-web-filter-service via
STOW-RS as part of its own project-assignment/indexing step. If the resent
files kept their original SOPInstanceUIDs, that STOW-RS call would be a
duplicate store of data dcm4chee had just accepted seconds earlier via this
DAG's own dcmsend step - dcm4chee rejects that, and dicom-web-filter-service
has no error handling around that specific call, surfacing as an opaque
500 that fails service-process-incoming-dcm before it ever reaches the step
that makes data queryable/indexed. Regenerating all three UID levels makes
the resent copy unambiguously new data to every downstream system, so no
collision is possible in the first place.

This DAG does NOT trigger segmentation itself - once the pair is correctly
tagged, the split-viewer's existing "Segment" button (which drives
auto-segmentation-pipeline unmodified) and OHIF's existing click-to-SLIM
lookup (body_part_matching.find_matching_sm_series, purely DICOM-tag based)
just work, the same way they already do for any pair that was never
mistagged in the first place.
"""

RADIOLOGY_MODALITIES = {"CT", "MR"}
WSI_MODALITIES = {"SM"}

# Matches this task's own `name` below - KaapanaPythonBaseOperator defaults
# operator_out_dir to the task's name/task_id, but a plain python_callable
# has no `self` to read that back from, so it's named as a shared constant
# instead of being duplicated as a literal string in two places.
RESOLVE_TASK_NAME = "resolve_and_retag"

logger = logging.getLogger(__name__)


def _read_modality_and_patient_id(dcm_dir: str):
    dcm_files = glob.glob(os.path.join(dcm_dir, "*.dcm"))
    if not dcm_files:
        return None
    ds = pydicom.dcmread(dcm_files[0], stop_before_pixels=True)
    return getattr(ds, "Modality", None), getattr(ds, "PatientID", None)


def resolve_and_retag_callback(**kwargs):
    get_input_out_dir = kwargs["params"]["get_input_out_dir"]
    batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME
    batch_element_dirs = glob.glob(os.path.join(batch_dir, "*"))
    if len(batch_element_dirs) != 2:
        raise ValueError(
            f"wsi-mapping-pipeline expects exactly 2 selected series, got {len(batch_element_dirs)}"
        )

    body_part = (kwargs["dag_run"].conf.get("workflow_form") or {}).get("body_part") or None

    elements = []
    for batch_element_dir in batch_element_dirs:
        dcm_dir = os.path.join(batch_element_dir, get_input_out_dir)
        info = _read_modality_and_patient_id(dcm_dir)
        if info is None:
            raise ValueError(f"No DICOM files found under {dcm_dir}")
        modality, patient_id = info
        elements.append(
            {
                "series_uid": os.path.basename(batch_element_dir),
                "batch_element_dir": batch_element_dir,
                "dcm_dir": dcm_dir,
                "modality": modality,
                "patient_id": patient_id,
            }
        )

    radiology = next((e for e in elements if e["modality"] in RADIOLOGY_MODALITIES), None)
    pathology = next((e for e in elements if e["modality"] in WSI_MODALITIES), None)
    if radiology is None or pathology is None or radiology is pathology:
        raise ValueError(
            f"Expected one radiology series ({sorted(RADIOLOGY_MODALITIES)}) and "
            f"one WSI series ({sorted(WSI_MODALITIES)}), got modalities "
            f"{[e['modality'] for e in elements]!r}"
        )

    logger.info(
        "wsi-mapping-pipeline: radiology series=%s (modality=%s, PatientID=%s), "
        "pathology series=%s (modality=%s, PatientID=%s), body_part override=%r",
        radiology["series_uid"],
        radiology["modality"],
        radiology["patient_id"],
        pathology["series_uid"],
        pathology["modality"],
        pathology["patient_id"],
        body_part,
    )

    out_dir = os.path.join(pathology["batch_element_dir"], RESOLVE_TASK_NAME)
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # New Study/Series UID shared by every file in this corrected copy; each
    # file additionally gets its own new SOP Instance UID below. See the
    # module docstring for why this is required (avoids a duplicate-store
    # collision in Kaapana's own stock re-ingestion of the resent data).
    new_study_uid = generate_uid()
    new_series_uid = generate_uid()

    dcm_files = glob.glob(os.path.join(pathology["dcm_dir"], "*.dcm"))
    for dcm_file in dcm_files:
        ds = pydicom.dcmread(dcm_file)
        ds.PatientID = radiology["patient_id"]
        if body_part:
            ds.BodyPartExamined = body_part
        ds.StudyInstanceUID = new_study_uid
        ds.SeriesInstanceUID = new_series_uid
        new_sop_uid = generate_uid()
        ds.SOPInstanceUID = new_sop_uid
        ds.file_meta.MediaStorageSOPInstanceUID = new_sop_uid
        ds.save_as(os.path.join(out_dir, os.path.basename(dcm_file)), write_like_original=False)

    logger.info(
        "wsi-mapping-pipeline: rewrote PatientID (%s -> %s)%s on %d pathology file(s); "
        "new StudyInstanceUID=%s, new SeriesInstanceUID=%s",
        pathology["patient_id"],
        radiology["patient_id"],
        f" and BodyPartExamined={body_part!r}" if body_part else "",
        len(dcm_files),
        new_study_uid,
        new_series_uid,
    )

    ti = kwargs["ti"]
    ti.xcom_push(key="pathology_series_uid", value=pathology["series_uid"])


def build_delete_series_conf(kwargs) -> dict:
    """
    Scoped to the OLD pathology series' own (pre-retag) UID - cleans up the
    stale, wrongly-tagged original now that the corrected copy (generated
    under entirely new Study/Series/SOPInstanceUIDs in resolve_and_retag_callback)
    is already safely stored. Runs *after* dcm_send on purpose: with no UID
    overlap between the old and new copies there's nothing left to collide,
    so there's no reason to risk deleting before confirming the resend
    actually succeeded.
    """
    ti = kwargs["ti"]
    pathology_series_uid = ti.xcom_pull(task_ids=RESOLVE_TASK_NAME, key="pathology_series_uid")
    return {
        "data_form": {"identifiers": [pathology_series_uid]},
        "workflow_form": {"delete_complete_study": True},
    }


ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "body_part": {
                "title": "Body part",
                "description": "Force a body part onto the pathology slide's own DICOM "
                "tags, for when it doesn't already carry a recognizable one. Leave empty "
                "to keep whatever the slide already has.",
                "type": "string",
                "default": "",
                "enum": [""] + sorted(set(BODY_PART_TO_CANONICAL.values())),
            },
        },
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
    dag_id="wsi-mapping-pipeline",
    default_args=args,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag)

resolve_and_retag = KaapanaPythonBaseOperator(
    dag=dag,
    name=RESOLVE_TASK_NAME,
    python_callable=resolve_and_retag_callback,
    params={"get_input_out_dir": get_input.operator_out_dir},
    input_operator=get_input,
)

trigger_delete_old_pathology_series = DynamicConfDagTriggerOperator(
    dag=dag,
    trigger_dag_id="delete-series",
    trigger_mode="single",
    wait_till_done=True,
    use_dcm_files=False,
    delay=10,
    extra_conf_callable=build_delete_series_conf,
)

dcm_send = DcmSendOperator(
    dag=dag,
    input_operator=resolve_and_retag,
)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True,
    trigger_rule="none_failed",
)

get_input >> resolve_and_retag >> dcm_send >> trigger_delete_old_pathology_series >> clean
