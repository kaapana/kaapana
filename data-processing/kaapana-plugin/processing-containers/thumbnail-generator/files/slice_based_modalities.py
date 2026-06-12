import shutil
from pathlib import Path
from typing import List, Optional

import pydicom
from generic import convert_dicom_to_thumbnail
from kaapanapy.helper import get_opensearch_client, load_workflow_config
from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from kaapanapy.helper.HelperOpensearch import DicomTags
from kaapanapy.logger import get_logger
from kaapanapy.settings import OpensearchSettings
from opensearchpy import OpenSearch
from PIL import Image
from pydantic import BaseModel

logger = get_logger(__name__)


class SeriesCompletenessMetadata(BaseModel):
    """
    Model to hold metadata about the DICOM series' completeness and its associated thumbnail gathered from OpenSearch.
    """

    min_instance_number: int
    max_instance_number: int
    is_series_complete: bool
    thumbnail_instance_uid: Optional[str]
    missing_instance_numbers: List[int]


def generate_thumbnail_for_middle_slice(
    operator_in_dir: Path,
    operator_out_dir: Path,
    study_uid: str,
    series_uid: str,
    thumbnail_size: int,
) -> Optional[Image.Image]:
    """
    Generate a thumbnail image for the DICOM series by selecting the middle slice.
    Thumbnail will be CREATED even from incomplete series if no thumbnail found.
    Thumbnail will be UPDATED only if the series is complete.

    The selection order is intentionally tiered: prefer the exact middle slice,
    then fall back to the closest retrievable slice when metadata and stored
    instances disagree. This keeps thumbnail generation resilient while still
    converging to the true middle slice once a complete series is available.

    Args:
        input_dir (Path): Path to the directory containing DICOM files.
        output_dir (Path): Path to save the generated thumbnail.
        study_uid (str): UID for the study.
        series_uid (str): UID for the series.
        thumbnail_size (int): Size of the generated thumbnail.

    Returns:
        Image: The generated thumbnail as a PIL Image.
    """
    workflow_config = load_workflow_config()
    client = get_opensearch_client()

    project_form = workflow_config.get("project_form", {})
    opensearch_index = project_form.get(
        "opensearch_index", OpensearchSettings().default_index
    )

    series_metadata = _get_opensearch_series_metadata(
        client, opensearch_index, series_uid
    )

    if not series_metadata:
        logger.info("No series metadata found -> Not generating a thumbnail")
        return None

    middle_instance_number = (
        series_metadata.min_instance_number + series_metadata.max_instance_number
    ) // 2

    # Only persist a new thumbnail selection automatically when it is stable:
    # either the series is complete, or an incomplete series receives its first
    # chosen fallback slice.
    update_thumbnail_metadata = series_metadata.is_series_complete

    if series_metadata.is_series_complete:
        instance_uid = _get_instance_uid_from_local(
            operator_in_dir=operator_in_dir,
            operator_out_dir=operator_out_dir,
            middle_instance_number=middle_instance_number,
        )

        if not instance_uid:
            instance_uid = _get_instance_uid_from_pacs(
                operator_out_dir=operator_out_dir,
                middle_instance_number=middle_instance_number,
                study_uid=study_uid,
                series_uid=series_uid,
            )

        if not instance_uid:
            # Complete-series metadata can still drift from what is currently
            # downloadable. Fall back to the nearest valid slice instead of
            # failing the whole thumbnail task.
            logger.warning(
                "Exact middle slice lookup failed for a complete series; falling back to the closest available local slice."
            )
            instance_uid = _get_closest_instance_uid_from_local(
                operator_in_dir=operator_in_dir,
                operator_out_dir=operator_out_dir,
                target_instance_number=middle_instance_number,
            )

        if not instance_uid:
            # If local workflow data is missing the expected slice entirely,
            # search PACS metadata for the closest retrievable instance.
            logger.warning(
                "Local closest-slice fallback failed; falling back to the closest available PACS slice."
            )
            instance_uid = _get_closest_instance_uid_from_pacs(
                operator_out_dir=operator_out_dir,
                study_uid=study_uid,
                series_uid=series_uid,
                target_instance_number=middle_instance_number,
            )
    else:
        logger.info(
            "Series incomplete; creating an initial thumbnail from the best available slice."
        )

        if series_metadata.thumbnail_instance_uid:
            # Reuse the previously selected thumbnail slice so incomplete reruns stay stable
            # until the series becomes complete and a true middle slice can be chosen.
            instance_uid = _copy_instance_from_local_by_uid(
                operator_in_dir=operator_in_dir,
                operator_out_dir=operator_out_dir,
                instance_uid=series_metadata.thumbnail_instance_uid,
            )

            if not instance_uid:
                instance_uid = _download_instance_by_uid(
                    operator_out_dir=operator_out_dir,
                    study_uid=study_uid,
                    series_uid=series_uid,
                    instance_uid=series_metadata.thumbnail_instance_uid,
                )
        else:
            # Pick the locally available slice closest to the expected middle of the full
            # series so a first thumbnail can be created before missing instances arrive.
            instance_uid = _get_closest_instance_uid_from_local(
                operator_in_dir=operator_in_dir,
                operator_out_dir=operator_out_dir,
                target_instance_number=middle_instance_number,
            )
            update_thumbnail_metadata = bool(instance_uid)

    if not instance_uid:
        logger.error(
            f"Couldn't find SOPInstanceUID for InstanceNumber: {middle_instance_number}"
        )
        return None

    if update_thumbnail_metadata:
        # Persist the chosen slice so later incomplete reruns stay consistent and
        # complete-series reruns can replace it with the actual middle slice.
        series_metadata.thumbnail_instance_uid = instance_uid
        _update_opensearch_series_metadata(
            client, opensearch_index, series_uid, series_metadata
        )

    middle_slice_dicom_filename = operator_out_dir / f"{instance_uid}.dcm"

    if not middle_slice_dicom_filename.exists():
        logger.error("Series missing middle slice both in PACS and in local data")
        return None

    thumbnail = convert_dicom_to_thumbnail(middle_slice_dicom_filename, thumbnail_size)

    return thumbnail


def _get_instance_uid_from_local(
    operator_in_dir: Path, operator_out_dir: Path, middle_instance_number: int
) -> Optional[str]:
    """
    Retrieve the SOP Instance UID of the DICOM file in the middle of a series from local workflow_data.

    Args:
        dcm_dir (Path): The directory containing DICOM files.
        middle_instance_number (int): The instance number of the middle file in the series.

    Returns:
        str: The SOP Instance UID of the middle file.
    """
    for filename in operator_in_dir.iterdir():
        dcm_file = pydicom.dcmread(filename)
        if dcm_file.InstanceNumber == middle_instance_number:
            shutil.copy(filename, operator_out_dir / filename.name)
            return dcm_file.SOPInstanceUID
    return None


def _copy_instance_from_local_by_uid(
    operator_in_dir: Path, operator_out_dir: Path, instance_uid: str
) -> Optional[str]:
    """
    Copy a specific SOP instance from local workflow data into the working output directory.

    Args:
        operator_in_dir (Path): Directory containing local DICOM files.
        operator_out_dir (Path): Directory where the selected DICOM should be copied.
        instance_uid (str): SOP Instance UID of the desired slice.

    Returns:
        Optional[str]: The copied SOP Instance UID when found locally.
    """
    for filename in operator_in_dir.iterdir():
        dcm_file = pydicom.dcmread(filename, stop_before_pixels=True)
        if dcm_file.SOPInstanceUID == instance_uid:
            shutil.copy(filename, operator_out_dir / filename.name)
            return instance_uid
    return None


def _get_closest_instance_uid_from_local(
    operator_in_dir: Path, operator_out_dir: Path, target_instance_number: int
) -> Optional[str]:
    """
    Copy the locally available slice whose InstanceNumber is closest to the expected middle.

    Args:
        operator_in_dir (Path): Directory containing local DICOM files.
        operator_out_dir (Path): Directory where the selected DICOM should be copied.
        target_instance_number (int): Desired middle InstanceNumber of the full series.

    Returns:
        Optional[str]: The SOP Instance UID of the closest available local slice.
    """
    closest_candidate: tuple[int, str, Path] | None = None

    for filename in operator_in_dir.iterdir():
        dcm_file = pydicom.dcmread(filename, stop_before_pixels=True)
        instance_number = getattr(dcm_file, "InstanceNumber", None)
        instance_uid = getattr(dcm_file, "SOPInstanceUID", None)

        if instance_number is None or not instance_uid:
            continue

        distance = abs(int(instance_number) - target_instance_number)
        candidate = (distance, instance_uid, filename)
        if closest_candidate is None or candidate < closest_candidate:
            closest_candidate = candidate

    if not closest_candidate:
        return None

    _, instance_uid, filename = closest_candidate
    shutil.copy(filename, operator_out_dir / filename.name)
    return instance_uid


def _get_instance_uid_from_pacs(
    operator_out_dir: Path, middle_instance_number: int, study_uid: str, series_uid: str
):
    """
    Finds the SOPInstanceUID of the middle DICOM slice in a PACS.
    If found, also download the file into a operator_out_dir

    Args:
        dcm_dir (Path): Path to the directory containing the workflow DICOM files.
        middle_instance_number (int): The middle instance number of the DICOM series.
        study_uid (str): The StudyInstanceUID of the DICOM series.
        series_uid (str): The SeriesInstanceUID of the DICOM series.

    Returns:
        str: The SOPInstanceUID of the middle DICOM slice.
    """
    dcmweb_helper = HelperDcmWeb()
    instances = dcmweb_helper.get_instances_of_series(
        study_uid=study_uid,
        series_uid=series_uid,
        params={"InstanceNumber": middle_instance_number},
    )

    if len(instances) == 1:
        instance = instances[0]
        instance_uid = _extract_instance_uid(instance)

        if not instance_uid:
            return None

        dcmweb_helper.download_instance(
            study_uid=study_uid,
            series_uid=series_uid,
            instance_uid=instance_uid,
            target_dir=str(operator_out_dir),
        )
        return instance_uid


def _get_closest_instance_uid_from_pacs(
    operator_out_dir: Path,
    study_uid: str,
    series_uid: str,
    target_instance_number: int,
) -> Optional[str]:
    """
    Download the PACS slice whose InstanceNumber is closest to the expected middle.

    This is a last-resort fallback for cases where OpenSearch marks a series as
    complete but neither the exact target slice nor a matching local copy can be
    resolved anymore.

    Args:
        operator_out_dir (Path): Directory where the selected DICOM should be saved.
        study_uid (str): StudyInstanceUID of the series.
        series_uid (str): SeriesInstanceUID of the series.
        target_instance_number (int): Desired middle InstanceNumber of the full series.

    Returns:
        Optional[str]: The SOP Instance UID of the closest PACS slice.
    """
    dcmweb_helper = HelperDcmWeb()
    instances = dcmweb_helper.get_instances_of_series(
        study_uid=study_uid,
        series_uid=series_uid,
    )

    if not instances:
        return None

    closest_candidate: tuple[int, str] | None = None
    for instance in instances:
        instance_uid = _extract_instance_uid(instance)
        instance_number = _extract_instance_number(instance)

        if instance_number is None or not instance_uid:
            continue

        distance = abs(instance_number - target_instance_number)
        candidate = (distance, instance_uid)
        if closest_candidate is None or candidate < closest_candidate:
            closest_candidate = candidate

    if not closest_candidate:
        return None

    _, instance_uid = closest_candidate
    dcmweb_helper.download_instance(
        study_uid=study_uid,
        series_uid=series_uid,
        instance_uid=instance_uid,
        target_dir=str(operator_out_dir),
    )
    return instance_uid


def _download_instance_by_uid(
    operator_out_dir: Path, study_uid: str, series_uid: str, instance_uid: str
) -> Optional[str]:
    """
    Download a specific SOP instance by UID into the working output directory.

    Args:
        operator_out_dir (Path): Directory where the selected DICOM should be saved.
        study_uid (str): StudyInstanceUID of the series.
        series_uid (str): SeriesInstanceUID of the series.
        instance_uid (str): SOPInstanceUID to download.

    Returns:
        Optional[str]: The downloaded SOP Instance UID on success.
    """
    dcmweb_helper = HelperDcmWeb()
    dcmweb_helper.download_instance(
        study_uid=study_uid,
        series_uid=series_uid,
        instance_uid=instance_uid,
        target_dir=str(operator_out_dir),
    )
    return instance_uid


def _extract_instance_uid(instance: dict) -> Optional[str]:
    """
    Extract the SOPInstanceUID from PACS metadata that may be returned either as
    plain values or as DICOM JSON tag objects.

    Different DICOMweb paths in Kaapana return slightly different metadata
    shapes, so the thumbnail fallback code normalizes them here.
    """
    uid_value = instance.get("00080018")
    if isinstance(uid_value, dict):
        values = uid_value.get("Value", [])
        return values[0] if values else None
    return uid_value


def _extract_instance_number(instance: dict) -> Optional[int]:
    """
    Extract InstanceNumber from PACS metadata that may be returned either as
    plain values or as DICOM JSON tag objects.

    Normalizing the tag here keeps the closest-slice fallback logic independent
    from the specific DICOMweb response shape.
    """
    number_value = instance.get("00200013")
    if isinstance(number_value, dict):
        values = number_value.get("Value", [])
        number_value = values[0] if values else None

    if number_value is None:
        return None

    try:
        return int(number_value)
    except (TypeError, ValueError):
        return None


def _get_opensearch_series_metadata(
    client: OpenSearch, index: str, series_uid: str
) -> SeriesCompletenessMetadata | None:
    """
    Retrieve SeriesCompletenessMetadata from an OpenSearch instance.

    This function queries an OpenSearch instance to retrieve metadata about a DICOM series,
    specifically focusing on the completeness of the series. The function returns the metadata
    if it exists, otherwise returns `None`.

    Args:
        client (OpenSearch): An OpenSearch client instance.
        index (str): The name of the OpenSearch index containing the metadata.
        series_uid (str): The SeriesInstanceUID of the DICOM series.

    Returns:
        SeriesCompletenessMetadata | None: Metadata about the series completeness, or None if not found.
    """
    response = client.search(
        index=index,
        body={"query": {"match": {DicomTags.series_uid_tag: series_uid}}},
    )

    hits = response.get("hits", {}).get("hits", [])
    if hits:
        source = hits[0].get("_source", {})
        return SeriesCompletenessMetadata(
            min_instance_number=source.get(DicomTags.min_instance_number_tag),
            max_instance_number=source.get(DicomTags.max_instance_number_tag),
            is_series_complete=source.get(DicomTags.is_series_complete_tag),
            missing_instance_numbers=source.get(DicomTags.missing_instance_numbers_tag),
            thumbnail_instance_uid=source.get(DicomTags.thumbnail_instance_uid_tag, ""),
        )
    return None


def _update_opensearch_series_metadata(
    client: OpenSearch,
    index: str,
    series_uid: str,
    series_metadata: SeriesCompletenessMetadata,
):
    """
    Update thumbnail_instance_uid_tag in OpenSearch that indicated which instance was used for thumbnail.

    Args:
        client (OpenSearch): The OpenSearch client.
        index (str): The OpenSearch index name.
        series_uid (str): The SeriesInstanceUID of the DICOM series.
        series_metadata (SeriesCompletenessMetadata): The metadata to update.

    Returns:
        None
    """
    client.update(
        index=index,
        id=series_uid,
        body={
            "doc": {
                DicomTags.thumbnail_instance_uid_tag: series_metadata.thumbnail_instance_uid,
            },
            "doc_as_upsert": False,  # Do not insert if not exist and fail instead
        },
        refresh=True,
    )
    logger.info(f"Updated OpenSearch for Series {series_uid}")
    logger.info(f"min={series_metadata.min_instance_number}")
    logger.info(f"max={series_metadata.max_instance_number}")
    logger.info(f"is_series_complete={series_metadata.is_series_complete}")
    logger.info(f"missing={series_metadata.missing_instance_numbers}")
    logger.info(f"thumbnail_str={series_metadata.thumbnail_instance_uid}")
