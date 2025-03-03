from dataclasses import dataclass
import os
from pathlib import Path
from typing import List, Optional

from opensearchpy import OpenSearch
import pydicom
from kaapanapy.helper import get_opensearch_client, load_workflow_config
from kaapanapy.helper.HelperOpensearch import DicomTags
from kaapanapy.logger import get_logger
from kaapanapy.settings import OpensearchSettings, OperatorSettings
from kaapanapy.utils import (
    get_required_env_var,
    is_batch_mode,
    process_batches,
    process_single,
    validate_directory,
)

logger = get_logger(__name__)

processed_count = 0


@dataclass
class SeriesMetadata:
    """Represents metadata about a DICOM series retrieved from OpenSearch."""

    min_slice_index: int
    max_slice_index: int
    is_series_complete: bool
    missing_slices: Optional[List[int]] = None


def get_opensearch_series_metadata(
    client: OpenSearch, index: str, series_uid: str
) -> SeriesMetadata | None:
    response = client.search(
        index=index,
        body={"query": {"match": {"SeriesInstanceUID": series_uid}}},
    )

    hits = response.get("hits", {}).get("hits", [])
    if hits:
        source = hits[0].get("_source", {})
        return SeriesMetadata(
            min_slice_index=source.get(DicomTags.min_slice_index_tag),
            max_slice_index=source.get(DicomTags.max_slice_index_tag),
            is_series_complete=source.get(DicomTags.is_series_complete_tag),
            missing_slices=source.get(DicomTags.missing_slices_tag),
        )

    return None


def update_opensearch(
    client: OpenSearch, index: str, series_uid: str, series_metadata: SeriesMetadata
):
    client.update(
        index=index,
        id=series_uid,
        body={
            "doc": {
                DicomTags.min_slice_index_tag: series_metadata.min_slice_index,
                DicomTags.max_slice_index_tag: series_metadata.max_slice_index,
                DicomTags.is_series_complete_tag: series_metadata.is_series_complete,
            },
            "doc_as_upsert": False,  # Do not insert if not exist and fail instead
        },
        refresh=True,
    )
    logger.info(f"Updated OpenSearch for Series {series_uid}")
    logger.info(f"min={series_metadata.min_slice_index}")
    logger.info(f"max={series_metadata.max_slice_index}")
    logger.info(f"is_series_complete={series_metadata.is_series_complete}")
    logger.info(f"present_slices={series_metadata.missing_slices}")


def merge_metadata(
    old_series_metadata: SeriesMetadata, new_series_metadata: SeriesMetadata
) -> SeriesMetadata:
    min_slice_index = min(
        old_series_metadata.min_slice_index, new_series_metadata.min_slice_index
    )

    max_slice_index = min(
        old_series_metadata.max_slice_index, new_series_metadata.max_slice_index
    )

    merged_instance_mapping = {
        **old_series_metadata.missing_slices,
        **new_series_metadata.missing_slices,
    }
    # Determine expected slices based on the merged instance mapping
    expected_slices = set(range(min_slice_index, max_slice_index + 1))
    present_slices = set(merged_instance_mapping.keys())  # Keys are instance numbers

    missing_slices = expected_slices - present_slices
    is_series_complete = len(missing_slices) == 0

    # Return a new merged SeriesMetadata
    return SeriesMetadata(
        min_slice_index=min_slice_index,
        max_slice_index=max_slice_index,
        is_series_complete=is_series_complete,
        missing_slices=merged_instance_mapping,
    )


def check_completeness(operator_input_dir: Path, operator_out_dir: Path):
    """
    Checks if a DICOM series in `operator_input_dir` is complete by comparing
    the expected number of instances with the actual number of files present.

    Args:
        operator_input_dir (Path): The directory containing DICOM files.
    """
    global processed_count

    workflow_config = load_workflow_config()
    client = get_opensearch_client()

    project_form = workflow_config.get("project_form")
    if not project_form:
        opensearch_index = OpensearchSettings().default_index
    else:
        opensearch_index = project_form.get("opensearch_index")

    dicom_files = sorted(list(operator_input_dir.glob("*.dcm")))
    if not dicom_files:
        return False, "No DICOM files found in the directory."

    # Read metadata from the first DICOM file
    first_dcm = pydicom.dcmread(dicom_files[0])
    series_uid = first_dcm.SeriesInstanceUID
    modality = first_dcm.Modality

    if hasattr(first_dcm, "InstanceNumber"):
        pass

    if hasattr(first_dcm, "PatientPosition"):
        pass

    if hasattr(first_dcm, "FrameNumber"):
        pass

    if hasattr(first_dcm, "FrameReferenceTime"):
        pass

    

    # Handle slice-based modalities
    if not modality in ["CT", "MR", "PET", "PT", "SM"]:
        processed_count += 1
        return True, f"Completeness check not support for modality {modality}"

    if not hasattr(first_dcm, "InstanceNumber"):
        logger.error("InstanceNumber missing!")
        return (
            False,
            f"InstanceNumber tag missing in series: {series_uid} for modality {modality}.",
        )

    dicom_files = [pydicom.dcmread(f) for f in dicom_files]
    instance_mapping = {ds.InstanceNumber: ds.SOPInstanceUID for ds in dicom_files}

    # Determine min/max slice index
    min_slice = min(instance_mapping.keys())
    max_slice = max(instance_mapping.keys())

    expected_slices = set(range(min_slice, max_slice + 1))
    actual_slices = set(instance_mapping.keys())
    missing_slices = expected_slices - actual_slices
    is_series_complete = len(missing_slices) == 0

    old_series_metadata = get_opensearch_series_metadata(
        client, opensearch_index, series_uid
    )
    new_series_metadata = SeriesMetadata(
        min_slice_index=min_slice,
        max_slice_index=max_slice,
        is_series_complete=is_series_complete,
        missing_slices=instance_mapping,
    )
    if old_series_metadata:
        new_series_metadata = merge_metadata(
            old_series_metadata=old_series_metadata,
            new_series_metadata=new_series_metadata,
        )

    # if not old_series_metadata or new_series_metadata != old_series_metadata:
    update_opensearch(client, opensearch_index, series_uid, new_series_metadata)
    processed_count += 1
    return True, f"Successfully updated series: {series_uid}"


def main():
    try:
        # Airflow variables
        operator_settings = OperatorSettings()

        # Load required environment variables
        thread_count = int(get_required_env_var("THREADS", "3"))

        workflow_dir = Path(operator_settings.workflow_dir)
        batch_name = operator_settings.batch_name
        operator_in_dir = Path(operator_settings.operator_in_dir)
        operator_out_dir = Path(operator_settings.operator_out_dir)

        # Validate required directories
        workflow_dir = validate_directory(workflow_dir, "Workflow")
        batch_dir = validate_directory(os.path.join(workflow_dir, batch_name), "Batch")

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
            operator_input_dir=Path(operator_in_dir),
            operator_out_dir=Path(operator_out_dir),
            processing_function=check_completeness,
            thread_count=thread_count,
        )
    else:
        process_single(
            # Required
            base_dir=Path(workflow_dir),
            operator_input_dir=Path(operator_in_dir),
            operator_out_dir=Path(operator_out_dir),
            processing_function=check_completeness,
            thread_count=thread_count,
        )

    if processed_count == 0:
        logger.error("No files have been processed!")
        raise Exception("No files have been processed!")
    else:
        logger.info(f"{processed_count} files have been processed!")


if __name__ == "__main__":
    main()
