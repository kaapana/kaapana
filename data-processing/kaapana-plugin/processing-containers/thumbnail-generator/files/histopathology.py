from pathlib import Path
from typing import Optional

from generic import convert_dicom_to_thumbnail
from kaapanapy.logger import get_logger
from PIL import Image

logger = get_logger(__name__)


def generate_histopathology_thumbnail(
    operator_in_dir: Path, thumbnail_size: int
) -> Optional[Image.Image]:
    """
    Generates a thumbnail from a microscopy image.

    This function takes a directory containing DICOM files and generates a thumbnail
    image of the first microscopy image found in the directory. The thumbnail is
    resized to the specified thumbnail size.

    Args:
        operator_in_dir (Path): The directory containing the DICOM files.
        thumbnail_size (int): The size of the thumbnail image.

    Returns:
        Image: The generated thumbnail image.
    """
    dicom_files = list(operator_in_dir.glob("*.dcm"))

    if not dicom_files:
        raise ValueError("No DICOM files found in the directory.")

    thumbnail = convert_dicom_to_thumbnail(dicom_files[0], thumbnail_size)
    return thumbnail
