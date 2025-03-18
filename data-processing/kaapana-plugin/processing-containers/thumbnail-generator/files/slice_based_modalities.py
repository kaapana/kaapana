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
) -> Image:
    """
    Generate a thumbnail image for the DICOM series by selecting the middle slice.
    Thumbnail will be CREATED even from incomplete series if no thumbnail found.
    Thumbnail will be UPDATED only if the series is complete.

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

    if not series_metadata.is_series_complete:
        logger.info("Not updating thumbnail using incomplete series.")
        return None

    middle_instance_number = (
        series_metadata.min_instance_number + series_metadata.max_instance_number
    ) // 2

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
        logger.error(
            f"Couldn't find SOPInstanceUID for InstanceNumber: {middle_instance_number}"
        )
        return None

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
) -> str:
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
        instance_uid = instance["00080018"]

        dcmweb_helper.download_instance(
            study_uid=study_uid,
            series_uid=series_uid,
            instance_uid=instance_uid,
            target_dir=operator_out_dir,
        )
        return instance_uid


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
