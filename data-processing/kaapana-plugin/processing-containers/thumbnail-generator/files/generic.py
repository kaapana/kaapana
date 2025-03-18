import os
import subprocess
import tempfile
import traceback
from pathlib import Path

import cv2
import numpy as np
import pydicom
from kaapanapy.logger import get_logger
from PIL import Image

logger = get_logger(__name__)


def generate_thumbnail_with_dcm2pnm(dcm_file: Path, thumbnail_size: int) -> Image:
    """
    Converts a DICOM file to a PNG image with a specified thumbnail size using dcmtk.
    https://support.dcmtk.org/docs-snapshot/dcm2pnm.html

    Args:
        dcm_file (Path): Path to the input DICOM file.
        thumbnail_size (int): Size of the thumbnail in pixels.

    Returns:
        Image: The resulting PNG image.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_png_file = os.path.join(tmp_dir, "thumbnail.png")
        dcm2pnm_command = [
            "dcm2pnm",
            "--debug",
            "--verbose",
            "--accept-acr-nema",
            "--scale-y-size",
            str(thumbnail_size),
            "+M",
            "+Wn",
            "--write-png",
            str(dcm_file),
            str(output_png_file),
        ]
        try:
            subprocess.run(
                dcm2pnm_command, check=True, stderr=subprocess.PIPE, text=True
            )
            thumbnail = Image.open(output_png_file)
            return thumbnail
        except subprocess.CalledProcessError as e:
            logger.error(e.stderr)
            raise RuntimeError(f"dcm2pnm failed: {e}")


def _apply_windowing(
    pixel_array: np.ndarray, dicom_ds: pydicom.FileDataset
) -> np.ndarray:
    """
    Apply windowing (VOI LUT or default) to the pixel data.

    This function adjusts the pixel intensity values based on DICOM windowing parameters.
    If a `VOILUTFunction` is present and set to `"SIGMOID"`, it applies a sigmoid transformation.
    Otherwise, it applies default linear windowing using `WindowCenter` and `WindowWidth`.

    Args:
        pixel_array (np.ndarray): A NumPy array representing the raw pixel data.
        dicom_ds (pydicom.dataset.FileDataset): The DICOM dataset containing metadata.

    Returns:
        np.ndarray: The windowed pixel array.

    """
    if "VOILUTFunction" in dicom_ds:
        logger.info("Applying VOI LUT function")
        voi_lut = dicom_ds.voi_lut_function
        if voi_lut == "SIGMOID":
            # Apply sigmoid transformation
            center = dicom_ds.WindowCenter
            width = dicom_ds.WindowWidth
            return 1 / (1 + np.exp(-((pixel_array - center) / width)))

    if "WindowCenter" in dicom_ds and "WindowWidth" in dicom_ds:
        logger.info("Applying default windowing")
        center = dicom_ds.WindowCenter
        width = dicom_ds.WindowWidth

        if isinstance(center, pydicom.multival.MultiValue):
            center = center[0]
        if isinstance(width, pydicom.multival.MultiValue):
            width = width[0]

        min_value = center - width / 2
        max_value = center + width / 2
        pixel_array = np.clip(pixel_array, min_value, max_value)

    return pixel_array


def _apply_rescale(
    pixel_array: np.ndarray, dicom_ds: pydicom.FileDataset
) -> np.ndarray:
    """
    Apply rescale slope and intercept to the DICOM pixel data.

    Some DICOM images store pixel values that need to be adjusted using a linear transformation:
        output_value = (pixel_value * RescaleSlope) + RescaleIntercept

    Args:
        pixel_array (np.ndarray): The raw pixel data from the DICOM file.
        dicom_ds (pydicom.dataset.FileDataset): The DICOM dataset containing metadata.

    Returns:
        np.ndarray: The rescaled pixel array.
    """
    slope = dicom_ds.RescaleSlope if "RescaleSlope" in dicom_ds else 1
    intercept = dicom_ds.RescaleIntercept if "RescaleIntercept" in dicom_ds else 0

    logger.debug(f"Applying rescale slope {slope}, intercept {intercept}")
    return pixel_array * slope + intercept


def _normalize_pixels(pixel_array: np.ndarray) -> np.ndarray:
    """
    Normalize pixel values to the 0-255 range for PNG saving.

    Args:
        pixel_array (np.ndarray): The pixel data after windowing and rescaling.

    Returns:
        np.ndarray: The normalized pixel data as an 8-bit unsigned integer array.
    """
    pixel_array = pixel_array - np.min(pixel_array)
    pixel_array = pixel_array / np.max(pixel_array) * 255.0
    return pixel_array.astype(np.uint8)


def dcm2pixel_array(dicom_ds: pydicom.FileDataset, expected_dim: int) -> np.ndarray:
    """
    Selects a slice (i.e., a specific depth in the image stack) from the DICOM dataset.

    Args:
        dicom_ds (pydicom.dataset.FileDataset): The DICOM dataset containing metadata and pixel data.

    Returns:
        np.ndarray: The selected slice as a NumPy array.
    """
    pixel_array = dicom_ds.pixel_array
    if pixel_array.ndim == expected_dim + 1:
        logger.info(
            f"Extra dimension detected. Selecting middle index of the first dimension (assuming slices): {pixel_array.shape}"
        )
        slice_index = pixel_array.shape[0] // 2
        pixel_array_slice = pixel_array[slice_index]
        return pixel_array_slice
    else:
        return pixel_array


def _convert_monochrome2(dicom_ds: pydicom.FileDataset) -> Image:
    """
    Convert a DICOM image to a thumbnail image using monochrome2 format used by most CT and MR

    This function processes the DICOM file to apply windowing, rescaling, and normalization,
    and then converts the pixel data to an 8-bit mono PNG image.

    Args:
        dicom_ds (pydicom.dataset.FileDataset): The DICOM dataset containing metadata and pixel data.

    Returns:
        Image: A PIL Image object representing the thumbnail.
    """
    pixel_array = dcm2pixel_array(dicom_ds, 2).astype(np.float32)
    pixel_array = _apply_rescale(pixel_array, dicom_ds)
    pixel_array = _apply_windowing(pixel_array, dicom_ds)
    pixel_array = _normalize_pixels(pixel_array)
    image = Image.fromarray(pixel_array).convert("L")
    return image


def _convert_rgb(dicom_ds: pydicom.FileDataset) -> Image:
    """
    Convert a DICOM image to a thumbnail using RGB format.

    Args:
        dicom_ds (pydicom.dataset.FileDataset): The DICOM dataset containing metadata and pixel data.

    Returns:
        Image: A PIL Image object representing the thumbnail.
    """
    pixel_array = dcm2pixel_array(dicom_ds, 3).astype(np.uint8)
    return Image.fromarray(pixel_array)


def _convert_ybr(dicom_ds: pydicom.FileDataset) -> Image:
    """
    Convert a DICOM image to a thumbnail using YBR format.

    Args:
        dicom_ds (pydicom.dataset.FileDataset): The DICOM dataset containing metadata and pixel data.

    Returns:
        Image: A PIL Image object representing the thumbnail.
    """
    pixel_array = dcm2pixel_array(dicom_ds, 3).astype(np.uint8)

    # Check if the photometric interpretation involves YBR formats that may require subsampling adjustments
    if dicom_ds.PhotometricInterpretation in [
        "YBR_FULL_422",
        "YBR_ICT",
        "YBR_RCT",
        "YBR_PARTIAL_420",
    ]:
        # For YBR_FULL_422, chroma (Cb, Cr) channels are downsampled.
        # We need to upsample these channels.

        # Extract Y, Cb, and Cr channels (assuming the pixel array is in YCrCb format)
        y_channel = pixel_array[:, :, 0]  # Y channel (luminance)
        cr_channel = pixel_array[:, :, 1]  # Cr channel (chrominance red)
        cb_channel = pixel_array[:, :, 2]  # Cb channel (chrominance blue)

        # Interpolate Cb and Cr channels to match Y channel size if necessary (for subsampling)
        if (
            cr_channel.shape[0] != y_channel.shape[0]
            or cr_channel.shape[1] != y_channel.shape[1]
        ):
            cr_channel = cv2.resize(
                cr_channel,
                (y_channel.shape[1], y_channel.shape[0]),
                interpolation=cv2.INTER_LINEAR,
            )
            cb_channel = cv2.resize(
                cb_channel,
                (y_channel.shape[1], y_channel.shape[0]),
                interpolation=cv2.INTER_LINEAR,
            )

        # Stack the channels back together
        ycrcb_image = np.stack([y_channel, cb_channel, cr_channel], axis=-1)

        # Convert from YCrCb to BGR (OpenCV uses BGR, but PIL uses RGB)
        bgr_image = cv2.cvtColor(ycrcb_image, cv2.COLOR_YCrCb2BGR)

    else:
        # If no chroma subsampling, convert directly from YCrCb to BGR (for other YBR types)
        bgr_image = cv2.cvtColor(pixel_array, cv2.COLOR_YCrCb2BGR)

    # Convert the BGR image to RGB (since PIL expects RGB)
    rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)

    # Return the image as a PIL object
    return Image.fromarray(rgb_image)


def _convert_palette(dicom_ds: pydicom.FileDataset) -> Image:
    """
    Convert a DICOM image to a thumbnail image using palette format, typically used by X-ray and ultrasound images.

    This function processes the DICOM file to apply windowing, rescaling, and normalization,
    and then converts the pixel data to an 8-bit color PNG image.

    Args:
        dicom_ds (pydicom.dataset.FileDataset): The DICOM dataset containing metadata and pixel data.

    Returns:
        Image: A PIL Image object representing the thumbnail.
    """
    pixel_array = dcm2pixel_array(dicom_ds, 2)

    if "PaletteColorLookupTableData" in dicom_ds:
        # Apply the palette color LUT if present
        palette_data = dicom_ds.PaletteColorLookupTableData
        num_colors = len(palette_data) // 3  # Assuming RGB palette

        # Reshape the palette data into an RGB lookup table
        rgb_palette = np.array(palette_data, dtype=np.uint8).reshape(num_colors, 3)
        # Use the pixel array as indices into the palette
        palette_image = rgb_palette[pixel_array.astype(int)]

        # Convert to Image and apply thumbnail size
        img = Image.fromarray(palette_image)

    elif (
        "RedPaletteColorLookupTableData" in dicom_ds
        and "GreenPaletteColorLookupTableData" in dicom_ds
        and "BluePaletteColorLookupTableData" in dicom_ds
    ):

        # Extract the individual color components from the DICOM dataset
        red_palette_data = dicom_ds.RedPaletteColorLookupTableData
        green_palette_data = dicom_ds.GreenPaletteColorLookupTableData
        blue_palette_data = dicom_ds.BluePaletteColorLookupTableData

        num_colors = len(red_palette_data)  # Assuming each component is the same size

        # Reshape each color component into a numpy array (assuming each is 1D)
        red_palette = np.array(red_palette_data, dtype=np.uint8)
        green_palette = np.array(green_palette_data, dtype=np.uint8)
        blue_palette = np.array(blue_palette_data, dtype=np.uint8)

        # Stack the components into an RGB palette
        rgb_palette = np.stack([red_palette, green_palette, blue_palette], axis=-1)

        # Use the pixel array as indices into the RGB palette
        palette_image = rgb_palette[pixel_array.astype(int)]

        # Convert to Image and apply thumbnail size
        img = Image.fromarray(palette_image)
    else:
        logger.warning(
            "No PaletteColorLookupTableData found in DICOM for PALETTE COLOR."
        )
        img = Image.fromarray(pixel_array)
    return img


def convert_dicom_to_thumbnail(dcm_file: str, thumbnail_size: int) -> Image:
    """
    Convert a DICOM file to a PNG image, applying windowing, VOI LUT, and rescaling.

    Args:
        dcm_file (str): Path to the input DICOM file.
        size (tuple[int, int]): Desired output image size (width, height).

    Returns:
        Image: A PIL Image object representing the processed DICOM slice.
    """
    dicom_ds = pydicom.dcmread(dcm_file)
    if dicom_ds.PhotometricInterpretation == "PALETTE COLOR":
        image = _convert_palette(dicom_ds)
    elif dicom_ds.PhotometricInterpretation in ["MONOCHROME1", "MONOCHROME2"]:
        image = _convert_monochrome2(dicom_ds)
    elif dicom_ds.PhotometricInterpretation == "RGB":
        image = _convert_rgb(dicom_ds)
    elif dicom_ds.PhotometricInterpretation in [
        "YBR_FULL",
        "YBR_FULL_422",
        "YBR_ICT",
        "YBR_RCT",
        "YBR_PARTIAL_420",
        "YBR_PARTIAL",
    ]:
        image = _convert_ybr(dicom_ds)
    else:
        logger.error(
            f"Not supported PhotometricInterpretation: {dicom_ds.PhotometricInterpretation}"
        )
        image = None

    if image:
        image.thumbnail((thumbnail_size, thumbnail_size))
    return image


def generate_generic_thumbnail(operator_in_dir: Path, thumbnail_size: int) -> Image:
    """
    Generates a thumbnail for DICOM files in a given directory.
    1. Try dcm2pnm
    2. Try converting pixel array to PIL

    Args:
        operator_in_dir (Path): Path to the directory containing the DICOM files.
        thumbnail_size (int): Size of the thumbnail in pixels.

    Returns:
        Image: The resulting PNG image.
    """
    dcm_file = list(operator_in_dir.iterdir())[0]
    try:
        return generate_thumbnail_with_dcm2pnm(dcm_file, thumbnail_size)
    except Exception as e:
        logger.warning("dcm2pnm failed")
        logger.warning(traceback.format_exc())

    try:
        return convert_dicom_to_thumbnail(dcm_file, thumbnail_size)
    except Exception as e:
        logger.error(traceback.format_exc())

    return None
