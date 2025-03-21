import os
from pathlib import Path
from typing import List, Optional

import pydicom
from kaapanapy.helper import get_opensearch_client, load_workflow_config
from kaapanapy.helper.HelperOpensearch import DicomTags
from kaapanapy.logger import get_logger
from kaapanapy.settings import OpensearchSettings, OperatorSettings
from kaapanapy.utils import (
    ConfigError,
    is_batch_mode,
    process_batches,
    process_single,
)
from opensearchpy import OpenSearch
from pydantic import BaseModel, ValidationError

logger = get_logger(__name__)


class SeriesCompletenessMetadata(BaseModel):
    """Represents metadata about a DICOM series completeness retrieved from OpenSearch."""

    min_instance_number: int
    max_instance_number: int
    is_series_complete: bool
    missing_instance_numbers: List[int]


def get_opensearch_series_metadata(
    client: OpenSearch, index: str, series_uid: str
) -> Optional[SeriesCompletenessMetadata]:
    response = client.search(
        index=index,
        body={"query": {"match": {DicomTags.series_uid_tag: series_uid}}},
    )

    hits = response.get("hits", {}).get("hits", [])
    if not hits:
        return None

    source = hits[0].get("_source", {})
    try:
        series_metadata = SeriesCompletenessMetadata(
            min_instance_number=source.get(DicomTags.min_instance_number_tag),
            max_instance_number=source.get(DicomTags.max_instance_number_tag),
            is_series_complete=source.get(DicomTags.is_series_complete_tag),
            missing_instance_numbers=source.get(DicomTags.missing_instance_numbers_tag),
        )
        return series_metadata
    except ValidationError as e:
        logger.error(
            "Series found in OpenSearch, but series completeness metadata are missing."
        )
        logger.error(e)
        return None


def update_opensearch(
    client: OpenSearch,
    index: str,
    series_uid: str,
    series_metadata: SeriesCompletenessMetadata,
):
    client.update(
        index=index,
        id=series_uid,
        body={
            "doc": {
                DicomTags.min_instance_number_tag: series_metadata.min_instance_number,
                DicomTags.max_instance_number_tag: series_metadata.max_instance_number,
                DicomTags.is_series_complete_tag: series_metadata.is_series_complete,
                DicomTags.missing_instance_numbers_tag: series_metadata.missing_instance_numbers,
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


def check_completeness(operator_in_dir: Path, operator_out_dir: Path):
    """
    Checks if a DICOM series in `operator_in_dir` is complete by comparing
    the expected number of instances with the actual number of files present.

    Push updated metadata to OpenSearch

    Args:
        operator_in_dir (Path): The directory containing DICOM files.
    """

    workflow_config = load_workflow_config()
    client = get_opensearch_client()

    project_form = workflow_config.get("project_form")
    if not project_form:
        opensearch_index = OpensearchSettings().default_index
    else:
        opensearch_index = project_form.get("opensearch_index")

    dicom_filenames = sorted(list(operator_in_dir.glob("*.dcm")))
    if not dicom_filenames:
        return False, "No DICOM files found in the directory."

    dicom_files = [
        pydicom.dcmread(dicom_filename) for dicom_filename in dicom_filenames
    ]
    series_uid = dicom_files[0].SeriesInstanceUID
    modality = dicom_files[0].Modality

    if len(dicom_files) == 1:
        dicom_files[0].InstanceNumber = "1"

    if all(
        [
            hasattr(ds, "InstanceNumber") and str(ds.InstanceNumber).isdigit()
            for ds in dicom_files
        ]
    ):

        instance_numbers = [ds.InstanceNumber for ds in dicom_files]
        min_instance_number = min(instance_numbers)
        max_instance_number = max(instance_numbers)
        expected_instance_numbers = set(
            range(min_instance_number, max_instance_number + 1)
        )

        missing_instance_numbers = expected_instance_numbers - set(instance_numbers)
        is_series_complete = len(missing_instance_numbers) == 0
        new_series_metadata = SeriesCompletenessMetadata(
            min_instance_number=min_instance_number,
            max_instance_number=max_instance_number,
            is_series_complete=is_series_complete,
            missing_instance_numbers=sorted(list(missing_instance_numbers)),
        )
        old_series_metadata = get_opensearch_series_metadata(
            client, opensearch_index, series_uid
        )
        if not old_series_metadata:
            updated_series_metadata = new_series_metadata
        else:
            updated_series_metadata = update_metadata(
                old_series_metadata=old_series_metadata,
                new_series_metadata=new_series_metadata,
            )

        update_opensearch(client, opensearch_index, series_uid, updated_series_metadata)
        return True, f"Successfully updated series: {series_uid}"
    else:
        logger.error(
            "Required Dicom Tag InstanceNumber must be present in all instances"
        )
        return (
            False,
            f"Required Dicom Tag missing in series: {series_uid} for modality {modality}.",
        )


def get_available_instance_numbers(metadata: SeriesCompletenessMetadata) -> set:
    """
    Returns a set of available instance numbers for a given DICOM series metadata.
    Calculated as complement of missing instance numbers to range (min, max).

    Args:
        metadata (SeriesMetadata): The metadata of the DICOM series.

    Returns:
        set: A set of available instance numbers.
    """
    full_range = set(
        range(metadata.min_instance_number, metadata.max_instance_number + 1)
    )
    return full_range - set(metadata.missing_instance_numbers)


def update_metadata(
    old_series_metadata: SeriesCompletenessMetadata,
    new_series_metadata: SeriesCompletenessMetadata,
) -> SeriesCompletenessMetadata:
    """
    Merges two series metadata objects, updating the instance numbers and completeness.

    The function calculates the updated `min_instance_number` and `max_instance_number`
    based on the existing and new series metadata. It then computes `missing_instance_numbers`
    as the instance numbers that are expected but not available in either of the metadata.
    Finally, it sets `is_series_complete` to `True` if there are no missing instance numbers,
    otherwise `False`.

    Args:
        old_series_metadata: The existing series metadata.
        new_series_metadata: The new series metadata to update with.

    Returns:
        The updated series metadata.
    """
    min_instance_number = min(
        old_series_metadata.min_instance_number, new_series_metadata.min_instance_number
    )

    max_instance_number = max(
        old_series_metadata.max_instance_number, new_series_metadata.max_instance_number
    )
    expected_instance_numbers = set(range(min_instance_number, max_instance_number + 1))
    old_available_instance_numbers = get_available_instance_numbers(old_series_metadata)
    new_available_instance_numbers = get_available_instance_numbers(new_series_metadata)
    missing_instance_numbers = (
        expected_instance_numbers
        - old_available_instance_numbers
        - new_available_instance_numbers
    )
    is_series_complete = len(missing_instance_numbers) == 0

    return SeriesCompletenessMetadata(
        min_instance_number=min_instance_number,
        max_instance_number=max_instance_number,
        is_series_complete=is_series_complete,
        missing_instance_numbers=sorted(list(missing_instance_numbers)),
    )


def main():
    try:
        # Airflow variables
        operator_settings = OperatorSettings()

        thread_count = int(os.getenv("THREADS", "3"))
        if thread_count is None:
            logger.error("Missing required environment variable: THREADS")
            raise ConfigError("Missing required environment variable: THREADS")

        workflow_dir = Path(operator_settings.workflow_dir)
        batch_name = operator_settings.batch_name
        operator_in_dir = Path(operator_settings.operator_in_dir)
        operator_out_dir = Path(operator_settings.operator_out_dir)

        if not workflow_dir.exists():
            logger.error(f"{workflow_dir} directory does not exist")
            raise ConfigError(f"{workflow_dir} directory does not exist")

        batch_dir = workflow_dir / batch_name
        if not batch_dir.exists():
            logger.error(f"{batch_dir} directory does not exist")
            raise ConfigError(f"{batch_dir} directory does not exist")

        logger.info(
            "All required directories and environment variables are validated successfully."
        )

    except Exception as e:
        logger.critical(f"Configuration error: {e}")
        raise SystemExit(1)  # Gracefully exit the program

    logger.info("Starting thumbnail generation")

    logger.info(f"thread_count: {thread_count}")
    logger.info(f"workflow_dir: {workflow_dir}")
    logger.info(f"batch_name: {batch_name}")
    logger.info(f"operator_in_dir: {operator_in_dir}")
    logger.info(f"operator_out_dir: {operator_out_dir}")

    batch_mode = is_batch_mode(workflow_dir=workflow_dir, batch_name=batch_name)

    if batch_mode:
        process_batches(
            # Required
            batch_dir=Path(batch_dir),
            operator_in_dir=Path(operator_in_dir),
            operator_out_dir=Path(operator_out_dir),
            processing_function=check_completeness,
            thread_count=thread_count,
        )
    else:
        process_single(
            # Required
            base_dir=Path(workflow_dir),
            operator_in_dir=Path(operator_in_dir),
            operator_out_dir=Path(operator_out_dir),
            processing_function=check_completeness,
            thread_count=thread_count,
        )


if __name__ == "__main__":
    main()
