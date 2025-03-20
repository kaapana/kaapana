import os
from pathlib import Path

import pydicom
from generic import generate_generic_thumbnail
from histopathology import generate_histopathology_thumbnail
from kaapanapy.logger import get_logger
from kaapanapy.settings import OperatorSettings
from kaapanapy.utils import ConfigError, is_batch_mode, process_batches, process_single
from overlay_modalities import (
    generate_rtstruct_thumbnail,
    generate_segmentation_thumbnail,
)
from PIL import Image
from pydicom.uid import EncapsulatedPDFStorage, RawDataStorage
from slice_based_modalities import generate_thumbnail_for_middle_slice

logger = get_logger(__name__)


def generate_thumbnail(
    operator_in_dir: Path,
    operator_out_dir: Path,
    operator_get_ref_series_dir: Path,
    thumbnail_size: int,
) -> tuple:
    """
    Generates thumbnails for a given set of DICOM files.

    This function processes a directory containing DICOM images and generates thumbnails based
    on specified modalities. The thumbnails are generated in a specified output directory.

    Modality Strategy for Thumbnail Creation:
    1. Slice-based Modalities:
        - CT, MR, PT, NM
        - Use the middle slice
    2. Overlay Modalities:
        - SEG, RTSTRUCT
        - Overlay over reference series
    3. Whole Slide Imaging Modalities:
        - SM, VL, DX
        - Use the highest resolution or overview image (SM)
    4. Others:
        - OT, PX, OP, XR
        - Use the first instance
        - Try dcm2pnm (https://support.dcmtk.org/docs-snapshot/dcm2pnm.html)
        - Try pixel_array + PIL

    Args:
        operator_in_dir (Path): The input directory containing the DICOM files.
        operator_out_dir (Path): The output directory where the thumbnails will be saved.
        operator_get_ref_series_dir (Path): The directory containing the reference series DICOM files.
        thumbnail_size (int): The size of the generated thumbnails.

    Returns:
        tuple: A tuple containing the total number of processed files and the total number of thumbnails generated.
    """

    logger.info(f"operator_in_dir: {operator_in_dir}")
    logger.info(f"operator_out_dir: {operator_out_dir}")

    if operator_get_ref_series_dir:
        logger.info(f"operator_get_ref_series_dir: {operator_get_ref_series_dir}")

    dicom_files = [pydicom.dcmread(filename) for filename in operator_in_dir.iterdir()]
    first_dcm = dicom_files[0]
    modality = first_dcm.Modality
    SOPClassUID = first_dcm.SOPClassUID

    study_uid = first_dcm.StudyInstanceUID
    series_uid = first_dcm.SeriesInstanceUID

    assert all(
        [ds.Modality == modality for ds in dicom_files]
    ), "Instances have different modalities"
    assert all(
        [ds.SeriesInstanceUID == series_uid for ds in dicom_files]
    ), "Instances have different SeriesUID"
    del dicom_files

    # thumbnail: Optional[Image.Image]
    if modality in ["CT", "MR", "PET", "NM"]:
        thumbnail = generate_thumbnail_for_middle_slice(
            operator_in_dir=operator_in_dir,
            operator_out_dir=operator_out_dir,
            study_uid=study_uid,
            series_uid=series_uid,
            thumbnail_size=thumbnail_size,
        )

    elif modality == "RTSTRUCT":
        thumbnail = generate_rtstruct_thumbnail(
            operator_in_dir, operator_get_ref_series_dir, thumbnail_size
        )
    elif modality == "SEG":
        thumbnail = generate_segmentation_thumbnail(
            operator_in_dir, operator_get_ref_series_dir, thumbnail_size
        )
    elif modality == "SM":
        thumbnail = generate_histopathology_thumbnail(operator_in_dir, thumbnail_size)

    elif SOPClassUID == EncapsulatedPDFStorage:
        thumbnail = Image.open("static/pdf.png")
    elif SOPClassUID == RawDataStorage:
        thumbnail = Image.open("static/raw.png")
    else:
        thumbnail = generate_generic_thumbnail(
            operator_in_dir=operator_in_dir,
            thumbnail_size=thumbnail_size,
        )

    if not thumbnail:
        raise Exception("Couldn't create thumbnail")

    target_png = os.path.join(operator_out_dir, f"new_{series_uid}.png")
    thumbnail.save(target_png)
    logger.info(f"Thumbnail saved to {target_png}")
    return True, target_png


def main():
    try:
        # Airflow variables
        operator_settings = OperatorSettings()

        # Load required environment variables
        thumbnail_size = int(os.getenv("SIZE", "300"))
        if thumbnail_size is None:
            logger.error("Missing required environment variable: SIZE")
            raise ConfigError("Missing required environment variable: SIZE")

        thread_count = int(os.getenv("THREADS", "3"))
        if thread_count is None:
            logger.error("Missing required environment variable: THREADS")
            raise ConfigError("Missing required environment variable: THREADS")

        operator_get_ref_series_dir = os.getenv("GET_REF_SERIES_OPERATOR_DIR")
        if operator_get_ref_series_dir is None:
            logger.error(
                "Missing required environment variable: GET_REF_SERIES_OPERATOR_DIR"
            )
            raise ConfigError(
                "Missing required environment variable: GET_REF_SERIES_OPERATOR_DIR"
            )

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

    except ConfigError as e:
        logger.critical(f"Configuration error: {e}")
        raise SystemExit(1)  # Gracefully exit the program

    logger.info("Starting thumbnail generation")

    logger.info(f"thumbnail_size: {thumbnail_size}")
    logger.info(f"thread_count: {thread_count}")
    logger.info(f"workflow_dir: {workflow_dir}")
    logger.info(f"batch_name: {batch_name}")
    logger.info(f"operator_in_dir: {operator_in_dir}")
    logger.info(f"operator_out_dir: {operator_out_dir}")
    logger.info(f"get_ref_series_dir: {operator_get_ref_series_dir}")

    batch_mode = is_batch_mode(workflow_dir=workflow_dir, batch_name=batch_name)

    if batch_mode:
        process_batches(
            # Extra parameters for the processing_function
            thumbnail_size=thumbnail_size,
            # Required
            batch_dir=batch_dir,
            operator_in_dir=operator_in_dir,
            operator_out_dir=operator_out_dir,
            processing_function=generate_thumbnail,
            thread_count=thread_count,
            # Optional
            operator_get_ref_series_dir=operator_get_ref_series_dir,
        )
    else:
        process_single(
            # Extra parameters for the processing_function
            thumbnail_size=thumbnail_size,
            # Required
            base_dir=workflow_dir,
            operator_in_dir=operator_in_dir,
            operator_out_dir=operator_out_dir,
            processing_function=generate_thumbnail,
            thread_count=thread_count,
            # Optional
            operator_get_ref_series_dir=operator_get_ref_series_dir,
        )


if __name__ == "__main__":
    main()
