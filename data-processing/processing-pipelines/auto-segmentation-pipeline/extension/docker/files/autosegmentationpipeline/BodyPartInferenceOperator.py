"""
Infers which body part a radiology (CT/MR) series covers by looking at the
DICOM metadata of the matching pathology (SM) study for the same patient -
this is the "resolve the anatomical region" step the combined radiology/
pathology viewer's organ-to-slide linking depends on.

Ported from combinedmodalityviewer's Kaapana_Extension/Auto-segmentation-pipeline/
.../autosegmentationpipeline/BodyPartInferenceOperator.py, rewritten:
- as a KaapanaPythonBaseOperator python_callable (matching the rest of this
  codebase's lightweight scheduler-side steps, e.g. trident-wsi's
  push_geojson_to_minio_callback), not a hand-rolled plain airflow.models.BaseOperator
- using kaapanapy's HelperDcmWeb (authenticated, project-aware, talks to
  dicom-web-filter-service) instead of unauthenticated direct requests to
  dcm4chee-arc
- the PatientID of the input study is read directly from the already-downloaded
  local DICOM file (GetInputOperator's output) instead of an extra PACS round
  trip - the file is already on disk in this execution context either way.

The tag-priority-order inference logic itself (study -> series -> first-
instance level, same fixed tag list) and the body-part normalization are kept
as-is from the original - that part was already sound.
"""
import glob
import logging
import os
import re
from pathlib import Path

import pydicom
from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb

from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME

logger = logging.getLogger(__name__)

# DICOM tags to check, in priority order (ported as-is from the original).
TAGS_TO_CHECK = [
    ("00180015", "value"),  # BodyPartExamined
    ("00082218", "code_meaning"),  # Anatomic Region Sequence
    ("00081084", "code_meaning"),  # Admitting Diagnoses Code Sequence
    ("00081030", "value"),  # StudyDescription
    ("0008103E", "value"),  # SeriesDescription
    ("00081080", "value"),  # Admitting Diagnoses Description
    ("00321060", "value"),  # Requested Procedure Description
    ("00321030", "value"),  # Reason for Study
    ("00181030", "value"),  # Protocol Name
]

# Canonical body parts this pipeline can currently recognize and act on (see
# the body-part -> total-segmentator-v2 task mapping in the DAG file for why
# this list is deliberately small - v2's "total" task already broadly covers
# most organs, so only body parts with a genuinely distinct specialized v2
# task need to be recognized here).
BODY_PART_TO_CANONICAL = {
    "heart": "heart",
    "liver": "liver",
    "spleen": "spleen",
    "kidney": "kidney",
    "kidneys": "kidney",
    "lung": "lung",
    "lungs": "lung",
    "aorta": "aorta",
    "brain": "brain",
    "prostate": "prostate",
}


def _get_tag_value(item: dict, tag: str):
    """Reads a plain tag value out of a DICOMweb JSON (QIDO/WADO) item."""
    if tag in item and "Value" in item[tag] and item[tag]["Value"]:
        return item[tag]["Value"][0]
    return None


def _get_code_meaning(item: dict, seq_tag: str):
    """Reads CodeMeaning (0008,0104) out of the first item of a coded sequence."""
    if seq_tag in item and "Value" in item[seq_tag]:
        for seq_item in item[seq_tag]["Value"]:
            if "00080104" in seq_item and "Value" in seq_item["00080104"]:
                return seq_item["00080104"]["Value"][0]
    return None


def _normalize_body_part(value) -> str | None:
    if not value:
        return None
    simple = re.sub(r"[^a-z ]", " ", str(value).lower())
    simple = re.sub(r"\s+", " ", simple).strip()

    if simple in BODY_PART_TO_CANONICAL:
        return BODY_PART_TO_CANONICAL[simple]
    for key in BODY_PART_TO_CANONICAL:
        if key in simple:
            return BODY_PART_TO_CANONICAL[key]
    if "carcinoma of prostate" in simple or "prostate carcinoma" in simple:
        return "prostate"
    return None


def _check_item_tags(item: dict) -> str | None:
    for tag, method in TAGS_TO_CHECK:
        val = _get_code_meaning(item, tag) if method == "code_meaning" else _get_tag_value(item, tag)
        if val:
            normalized = _normalize_body_part(val)
            if normalized:
                return normalized
    return None


def _find_sm_studies(helper: HelperDcmWeb, patient_id: str) -> list[dict]:
    """
    Not one of HelperDcmWeb's built-in methods (those are scoped to a known
    study) - composed the same way its own check_if_study_in_archive does:
    GET {dcmweb_rs_endpoint}/studies with QIDO-RS query params, through the
    same authenticated session.
    """
    url = f"{helper.dcmweb_rs_endpoint}/studies"
    params = {"PatientID": patient_id, "ModalitiesInStudy": "SM", "includefield": "all", "limit": 10}
    try:
        resp = helper.session.get(url, params=params)
        if resp.status_code == 204:
            return []
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Error querying dicom-web-filter for SM studies: %s", e)
        return []


def _get_series_of_study(helper: HelperDcmWeb, study_uid: str) -> list[dict]:
    """
    Not helper.get_series_of_study() - that convenience method issues its GET
    with no query params at all, so dcm4chee returns only its default minimal
    QIDO-RS attribute set. BodyPartExamined (and every other tag in
    TAGS_TO_CHECK) is an "additional" field that only comes back with an
    explicit includefield - confirmed by direct QIDO query against this
    cluster's archive: the body-part tag genuinely is indexed and correct at
    the series level, but helper.get_series_of_study()'s response simply
    never contains it. Composed the same way _find_sm_studies() already is.
    """
    url = f"{helper.dcmweb_rs_endpoint}/studies/{study_uid}/series"
    try:
        resp = helper.session.get(url, params={"includefield": "all"})
        if resp.status_code == 204:
            return []
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Error querying dicom-web-filter for series of study %s: %s", study_uid, e)
        return []


def _get_instances_of_series(helper: HelperDcmWeb, study_uid: str, series_uid: str) -> list[dict]:
    """Same includefield fix as _get_series_of_study(), for the instance level."""
    url = f"{helper.dcmweb_rs_endpoint}/studies/{study_uid}/series/{series_uid}/instances"
    try:
        resp = helper.session.get(url, params={"includefield": "all"})
        if resp.status_code == 204:
            return []
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(
            "Error querying dicom-web-filter for instances of series %s: %s", series_uid, e
        )
        return []


def _infer_body_part_from_sm(helper: HelperDcmWeb, sm_studies: list[dict]) -> str | None:
    # 1. Study level
    for study in sm_studies:
        body_part = _check_item_tags(study)
        if body_part:
            return body_part

    # 2. Series level, then 3. first-instance level
    for study in sm_studies:
        study_uid = _get_tag_value(study, "0020000D")
        if not study_uid:
            continue
        for series in _get_series_of_study(helper, study_uid):
            body_part = _check_item_tags(series)
            if body_part:
                return body_part

            series_uid = _get_tag_value(series, "0020000E")
            if not series_uid:
                continue
            instances = _get_instances_of_series(helper, study_uid, series_uid)
            if instances:
                body_part = _check_item_tags(instances[0])
                if body_part:
                    return body_part
    return None


def infer_body_part_callback(ds, **kwargs):
    """
    KaapanaPythonBaseOperator python_callable. Expects a single selected batch
    element (this DAG keeps workflow_form.single_execution read-only True, same
    as the original design). Returns the inferred canonical body part string,
    or None if nothing could be inferred - auto-pushed to XCom under the
    default key, consumed downstream via xcom_pull(task_ids="infer_body_part").
    """
    dicom_operator_out_dir = kwargs["params"]["dicom_operator_out_dir"]
    batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME

    batch_element_dirs = glob.glob(os.path.join(batch_dir, "*"))
    if not batch_element_dirs:
        logger.warning("No batch-element directories found under %s", batch_dir)
        return None

    dicom_dir = os.path.join(batch_element_dirs[0], dicom_operator_out_dir)
    dcm_files = glob.glob(os.path.join(dicom_dir, "*.dcm"))
    if not dcm_files:
        logger.warning("No DICOM files found under %s", dicom_dir)
        return None

    ds_local = pydicom.dcmread(dcm_files[0], stop_before_pixels=True)

    # Pushed under its own xcom key (not the callback's default return value,
    # which is the inferred body part) so build_total_segmentator_v2_conf()
    # can set workflow_form.input to the series' *actual* modality instead
    # of hardcoding "CT" - total-segmentator-v2's own get-input-data task
    # rejects a series whose modality isn't in that list (see get_input.py's
    # check_modality_of_workflow()), which previously broke every MR series.
    modality = getattr(ds_local, "Modality", None)
    if modality:
        kwargs["ti"].xcom_push(key="modality", value=modality)

    # Manual override via this DAG's own ui_forms.workflow_form.body_part
    # field. Short-circuits the SM-metadata inference below entirely when
    # present.
    manual_body_part = (kwargs["dag_run"].conf.get("workflow_form") or {}).get("body_part")
    if manual_body_part:
        logger.info("Using manually-specified body part: %s", manual_body_part)
        return manual_body_part

    patient_id = getattr(ds_local, "PatientID", None)
    if not patient_id:
        logger.warning("Could not read PatientID from %s", dcm_files[0])
        return None

    helper = HelperDcmWeb()
    sm_studies = _find_sm_studies(helper, patient_id)
    if not sm_studies:
        logger.warning("No SM studies found for PatientID: %s", patient_id)
        return None

    body_part = _infer_body_part_from_sm(helper, sm_studies)
    if body_part:
        logger.info("Inferred body part: %s", body_part)
    else:
        logger.warning("Could not infer body part from SM metadata.")
    return body_part
