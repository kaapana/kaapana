"""
Resolves the pathology (SM) series whose own DICOM metadata matches a given
organ/body-part label, for the same patient as a given radiology study - the
"click a segmented organ in OHIF, reveal the matching slide in SLIM" step of
the native dataset-browser integration.

The canonicalization table/tag-priority list is intentionally duplicated here
rather than imported from kaapanapy's own copy (used by the
auto-segmentation-pipeline DAG's BodyPartInferenceOperator - see
data-processing/processing-pipelines/auto-segmentation-pipeline/extension/docker/files/autosegmentationpipeline/BodyPartInferenceOperator.py):
kaapanapy lives in the shared base-python-cpu image every operator inherits
from, so changing it would force a base-image rebuild/version bump across the
whole operator fleet for this one feature. Keep both copies in sync by hand
if the tag list or canonicalization rules change.
"""
import re
from typing import Any, Dict, List, Optional

from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb

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
CANONICAL_BODY_PARTS = sorted(set(BODY_PART_TO_CANONICAL.values()))


def _get_tag_value(item: Dict[str, Any], tag: str) -> Optional[str]:
    if tag in item and "Value" in item[tag] and item[tag]["Value"]:
        return item[tag]["Value"][0]
    return None


def _get_code_meaning(item: Dict[str, Any], seq_tag: str) -> Optional[str]:
    if seq_tag in item and "Value" in item[seq_tag]:
        for seq_item in item[seq_tag]["Value"]:
            if "00080104" in seq_item and "Value" in seq_item["00080104"]:
                return seq_item["00080104"]["Value"][0]
    return None


def canonicalize_body_part(value: Optional[str]) -> Optional[str]:
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


def _check_item_tags(item: Dict[str, Any]) -> Optional[str]:
    for tag, method in TAGS_TO_CHECK:
        val = _get_code_meaning(item, tag) if method == "code_meaning" else _get_tag_value(item, tag)
        if val:
            canonical = canonicalize_body_part(val)
            if canonical:
                return canonical
    return None


def _find_study_by_uid(helper: HelperDcmWeb, study_instance_uid: str) -> Optional[Dict[str, Any]]:
    url = f"{helper.dcmweb_rs_endpoint}/studies"
    params = {"StudyInstanceUID": study_instance_uid, "includefield": "all", "limit": 1}
    resp = helper.session.get(url, params=params)
    if resp.status_code == 204:
        return None
    resp.raise_for_status()
    results = resp.json()
    return results[0] if results else None


def _find_sm_studies(helper: HelperDcmWeb, patient_id: str) -> List[Dict[str, Any]]:
    url = f"{helper.dcmweb_rs_endpoint}/studies"
    params = {"PatientID": patient_id, "ModalitiesInStudy": "SM", "includefield": "all", "limit": 10}
    resp = helper.session.get(url, params=params)
    if resp.status_code == 204:
        return []
    resp.raise_for_status()
    return resp.json()


def _get_series_of_study(helper: HelperDcmWeb, study_uid: str) -> List[Dict[str, Any]]:
    """
    Not helper.get_series_of_study() - that kaapanapy convenience method
    issues its GET with no query params at all, so dcm4chee returns only its
    default minimal QIDO-RS attribute set. Every tag in TAGS_TO_CHECK
    (BodyPartExamined included) is an "additional" field that only comes
    back with an explicit includefield - confirmed by direct QIDO query
    against this cluster's archive: the body-part tag genuinely is indexed
    and correct at the series level, but helper.get_series_of_study()'s
    response simply never contains it.
    """
    url = f"{helper.dcmweb_rs_endpoint}/studies/{study_uid}/series"
    resp = helper.session.get(url, params={"includefield": "all"})
    if resp.status_code == 204:
        return []
    resp.raise_for_status()
    return resp.json()


def _get_instances_of_series(
    helper: HelperDcmWeb, study_uid: str, series_uid: str
) -> List[Dict[str, Any]]:
    """Same includefield fix as _get_series_of_study(), for the instance level."""
    url = f"{helper.dcmweb_rs_endpoint}/studies/{study_uid}/series/{series_uid}/instances"
    resp = helper.session.get(url, params={"includefield": "all"})
    if resp.status_code == 204:
        return []
    resp.raise_for_status()
    return resp.json()


def find_matching_sm_series(
    helper: HelperDcmWeb, study_instance_uid: str, label: Optional[str] = None
) -> Dict[str, Any]:
    """
    Returns {smStudyUID, smSeriesUID, matchedBodyPart} for the SM series whose
    metadata resolves to the same canonical body part as `label` (the clicked
    segment's label), for the same patient as `study_instance_uid`. Returns {}
    if nothing tag-matches `label` - clicking an organ this patient has no
    corresponding pathology slide for should do nothing, not reveal an
    unrelated slide (no "first SM series found" fallback here on purpose).
    """
    study = _find_study_by_uid(helper, study_instance_uid)
    if not study:
        return {}
    patient_id = _get_tag_value(study, "00100020")
    if not patient_id:
        return {}

    wanted_canonical = canonicalize_body_part(label)
    if not wanted_canonical:
        return {}

    sm_studies = _find_sm_studies(helper, patient_id)
    if not sm_studies:
        return {}

    for sm_study in sm_studies:
        sm_study_uid = _get_tag_value(sm_study, "0020000D")
        if not sm_study_uid:
            continue
        for series in _get_series_of_study(helper, sm_study_uid) or []:
            sm_series_uid = _get_tag_value(series, "0020000E")
            if not sm_series_uid:
                continue

            canonical = _check_item_tags(sm_study) or _check_item_tags(series)
            if not canonical:
                instances = _get_instances_of_series(helper, sm_study_uid, sm_series_uid)
                if instances:
                    canonical = _check_item_tags(instances[0])

            if canonical == wanted_canonical:
                return {
                    "smStudyUID": sm_study_uid,
                    "smSeriesUID": sm_series_uid,
                    "matchedBodyPart": canonical,
                }

    return {}
