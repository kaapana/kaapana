import logging
import os
from dataclasses import dataclass
from glob import glob
from multiprocessing.pool import ThreadPool
from os import getenv
from os.path import exists, join
from pathlib import Path
from random import randint

import cv2
import numpy as np
import pydicom
import SimpleITK as sitk
from colormath.color_conversions import convert_color
from colormath.color_objects import LabColor, sRGBColor
from logger_helper import get_logger
from PIL import Image, ImageDraw, ImageFilter

log_level = getenv("LOG_LEVEL", "warning").lower()

log_levels = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

log_level_int = log_levels.get(log_level, logging.INFO)

logger = get_logger(__name__, log_level_int)

processed_count = 0


@dataclass
class Slice:
    slice_index: int
    segmentation_classes: list
    number_of_classes: int
    number_of_foreground_pixels: int


def dicomlab2LAB(dicomlab: list) -> list:
    """Converts DICOM Lab values to CIELab values

    Args:
        dicomlab (list): DICOM Lab values

    Returns:
        list: CIELab values
    """
    lab = [
        (dicomlab[0] * 100.0) / 65535.0,
        (dicomlab[1] * 255.0) / 65535.0 - 128,
        (dicomlab[2] * 255.0) / 65535.0 - 128,
    ]
    return lab


def crop_image_and_segmentation_to_overlapping_region(image, segmentation):
    """Crops the image and segmentation to the overlapping region.

    Args:
        image (sitk.Image): Reference image
        segmentation (sitk.Image): DICOM Segmentation object

    Returns:
        tuple: Tuple containing the cropped image and segmentation
    """

    # Handle 3D segmentation (ignore singleton fourth dimension)
    if len(segmentation.GetSize()) == 4 and segmentation.GetSize()[3] == 1:
        size = list(segmentation.GetSize())
        size[3] = 0  # Set the size of the fourth dimension to 0 (removes it)
        index = [0, 0, 0, 0]  # Start index at [0, 0, 0, 0]
        # Extract the 3D volume from the 4D image
        segmentation = sitk.Extract(segmentation, size=size, index=index)

    # Resample segmentation to match the reference image
    resample = sitk.ResampleImageFilter()
    resample.SetReferenceImage(image)
    resample.SetInterpolator(sitk.sitkNearestNeighbor)
    resample.SetDefaultPixelValue(0)
    resample.SetOutputPixelType(segmentation.GetPixelID())
    segmentation_resampled = resample.Execute(segmentation)

    # Compute the overlapping region size
    size = [
        min(image.GetSize()[i], segmentation_resampled.GetSize()[i]) for i in range(3)
    ]
    index = [0, 0, 0]  # Starting index (assuming images are aligned)

    # Crop both images to the overlapping region
    roi_filter = sitk.RegionOfInterestImageFilter()
    roi_filter.SetSize(size)
    roi_filter.SetIndex(index)
    image_cropped = roi_filter.Execute(image)
    segmentation_cropped = roi_filter.Execute(segmentation_resampled)

    # Check if the cropped images have the same size
    assert (
        image_cropped.GetSize() == segmentation_cropped.GetSize()
    ), f"Image and segmentation have different sizes: Image: {image_cropped.GetSize()}, Segmentation: {segmentation_cropped.GetSize()}"

    return image_cropped, segmentation_cropped


def create_thumbnail(parameters: tuple) -> tuple:
    """Creates a thumbnail image from a DICOM segmentation object or RTSTRUCT file

    Args:
        parameters (tuple): Tuple containing the paths to the DICOM segmentation object or RTSTRUCT file, the DICOM image directory, and the target directory

    Returns:
        tuple: Tuple containing a boolean indicating success and the path to the generated thumbnail
    """
    global processed_count

    dcm_seg_dir, dcm_dir, target_dir = parameters

    logger.info(f"dcm_seg_dir: {dcm_seg_dir}")
    logger.info(f"dcm_dir: {dcm_dir}")
    logger.info(f"target_dir: {target_dir}")

    # Load the DICOM segmentation object or RTSTRUCT file to determine the modality and series UID
    ds = pydicom.dcmread(os.path.join(dcm_seg_dir, os.listdir(dcm_seg_dir)[0]))
    modality = ds.Modality
    seg_series_uid = ds.SeriesInstanceUID

    # Create the target directory if it does not exist
    os.makedirs(target_dir, exist_ok=True)

    # Load the image and segmentation (and segment colors)
    if modality == "RTSTRUCT":
        image_array, seg_array, segment_colors = (
            load_image_and_segmenation_from_rtstruct(dcm_dir, dcm_seg_dir)
        )
    elif modality == "SEG":
        image_array, seg_array, segment_colors = (
            load_image_and_segmenation_from_dicom_segmentation(dcm_dir, dcm_seg_dir)
        )
    else:
        logger.error(f"Modality {modality} not supported")
        return False, ""

    # Convert the segmentation to a binary mask
    seg_array_binary = np.where(seg_array > 0, 1, 0)

    # Get Slices with most segmentation classes
    slices = []

    for i in range(image_array.shape[0]):
        slice_seg_array = seg_array[i, :, :]
        slice_seg_array_binary = seg_array_binary[i, :, :]

        number_of_classes = len(np.unique(slice_seg_array))
        number_of_foreground_pixels = np.sum(slice_seg_array_binary)

        slice = Slice(
            slice_index=i,
            segmentation_classes=np.unique(slice_seg_array),
            number_of_classes=number_of_classes,
            number_of_foreground_pixels=number_of_foreground_pixels,
        )

        slices.append(slice)

    # Find the slice with the most segmentation classes. If there are multiple slices with the same number of classes, choose the one with the most foreground pixels
    slices.sort(
        key=lambda x: (x.number_of_classes, x.number_of_foreground_pixels), reverse=True
    )

    # Select the best slice
    best_slice = slices[0]

    logger.info(
        f"Best slice: {best_slice.slice_index} with {best_slice.number_of_classes} classes and {best_slice.number_of_foreground_pixels} foreground pixels"
    )

    # Select the best image slice
    base_image_array = image_array[best_slice.slice_index, :, :]
    del image_array

    # Select the corresponding segmentation
    base_seg_array = seg_array[best_slice.slice_index, :, :]
    del seg_array

    # Select the corresponding binary mask
    base_seg_array_binary = seg_array_binary[best_slice.slice_index, :, :]
    del seg_array_binary

    # Use the binary mask to get the relevant intensities (To see the regions within the mask better)
    masked_array = base_image_array * base_seg_array_binary

    # Calculate the min and max intensity values within the masked region
    min_intensity = np.min(masked_array[masked_array > 0])
    max_intensity = np.max(masked_array[masked_array > 0])

    # Add a 10% margin to the min and max intensities
    margin = 0.1 * (max_intensity - min_intensity)
    window_min = max(0, min_intensity - margin)
    window_max = min(4095, max_intensity + margin)  # assuming 12-bit DICOM images

    # Apply windowing to the original DICOM image
    windowed_data = np.clip(base_image_array, window_min, window_max)

    del base_image_array

    # Normalize the windowed pixel values to 0-255
    normalized_data = (windowed_data - window_min) / (window_max - window_min) * 255
    normalized_data = normalized_data.astype(np.uint8)

    # Create an RGBA image from the normalized data
    image = Image.fromarray(normalized_data).convert("RGBA")

    # Draw the segment borders and fill the inner part with the segment color
    for seg_class in np.unique(base_seg_array):
        if seg_class == 0:
            continue
        color = segment_colors[seg_class]["color"]
        mask = Image.fromarray(np.uint8(base_seg_array == seg_class) * 255, mode="L")

        # Draw the border with full opacity
        border_overlay = Image.new("RGBA", image.size, tuple(color) + (255,))
        image = Image.composite(
            border_overlay, image, mask.filter(ImageFilter.FIND_EDGES)
        )

        # Draw the inner part with 50% transparency
        fill_overlay = Image.new("RGBA", image.size, tuple(color) + (0,))
        draw = ImageDraw.Draw(fill_overlay)
        draw.bitmap((0, 0), mask, fill=tuple(color) + (128,))

        image = Image.alpha_composite(image, fill_overlay)

    # Save the thumbnail
    target_png = os.path.join(target_dir, f"{seg_series_uid}.png")
    image.save(target_png)
    logger.info(f"Thumbnail saved to {target_png}")

    processed_count += 1

    return True, target_png


def load_image_and_segmenation_from_dicom_segmentation(
    image_dir: str, seg_dir: str
) -> tuple:
    """Load the image and segmentation from a DICOM segmentation object

    Args:
        image_dir (str): Directory containing the DICOM image files
        seg_dir (str): Directory containing the DICOM segmentation object

    Returns:
        tuple: Tuple containing the image array, segmentation array, and segment colors
    """

    # Load the image
    image_reader = sitk.ImageSeriesReader()

    dicom_names = image_reader.GetGDCMSeriesFileNames(image_dir)
    image_reader.SetFileNames(dicom_names)

    dicom_image = image_reader.Execute()
    image_array = sitk.GetArrayFromImage(dicom_image)

    # Load the segmentation
    file_name = os.path.join(seg_dir, os.listdir(seg_dir)[0])
    dicom_seg = pydicom.dcmread(file_name)

    seg_array = dicom_seg.pixel_array

    # Check segmentation and image dimensions
    if image_array.shape != seg_array.shape:

        # We will crop the image by the slices, which have a segmentation
        reader = sitk.ImageSeriesReader()
        dicom_names = reader.GetGDCMSeriesFileNames(seg_dir)
        reader.SetFileNames(dicom_names)

        # crop the image to the segmented region
        cropped_image, cropped_seg = crop_image_and_segmentation_to_overlapping_region(
            image=dicom_image, segmentation=reader.Execute()
        )

        image_array = sitk.GetArrayFromImage(cropped_image)
        seg_array = sitk.GetArrayFromImage(cropped_seg)

        del cropped_image
        del cropped_seg

    del dicom_image

    # Iterate through the segments and extract the colors
    segment_colors = {}

    # Look up the color for each class from dicom seg ob
    if "SegmentSequence" in dicom_seg:
        for segment in dicom_seg.SegmentSequence:
            segment_number = segment.SegmentNumber
            segment_label = segment.SegmentLabel

            # Extract the color information
            if hasattr(segment, "RecommendedDisplayCIELabValue"):
                cie_lab_color_int = segment.RecommendedDisplayCIELabValue
                cie_lab_color_float = [float(int(x)) for x in cie_lab_color_int]
                color_rgb = dicomlab2LAB(dicomlab=cie_lab_color_float)
                lab = LabColor(color_rgb[0], color_rgb[1], color_rgb[2])
                color_rgb = convert_color(lab, sRGBColor).get_upscaled_value_tuple()
                color = [max(min(x, 255), 0) for x in color_rgb]
                color_type = "CIELab"
            elif hasattr(segment, "RecommendedDisplayRGBValue"):
                color = segment.RecommendedDisplayRGBValue
                color_type = "RGB"
            else:
                # If no color information is available, generate a random color
                color = [randint(0, 255), randint(0, 255), randint(0, 255)]
                color_type = "Random"

            segment_colors[segment_number] = {
                "label": segment_label,
                "color_type": color_type,
                "color": color,
            }

    # Check if the segmentation is binary but encoded as 0 and 255
    if np.array_equal(np.unique(seg_array), np.array([0, 255])):
        seg_array = np.where(seg_array == 255, 1, 0)

    return image_array, seg_array, segment_colors


def load_image_and_segmenation_from_rtstruct(
    image_dir: str, rt_struct_dir: str
) -> tuple:
    """Load the image and segmentation from an RTSTRUCT file

    Args:
        image_dir (str): Directory containing the DICOM image files
        rt_struct_dir (str): Directory containing the RTSTRUCT file

    Returns:
        tuple: Tuple containing the image array, segmentation array, and segment colors
    """

    # Load the RTSTRUCT
    rtstruct = pydicom.dcmread(
        os.path.join(rt_struct_dir, os.listdir(rt_struct_dir)[0])
    )

    # Load the image
    image_reader = sitk.ImageSeriesReader()
    dicom_names = image_reader.GetGDCMSeriesFileNames(image_dir)
    image_reader.SetFileNames(dicom_names)
    dicom_image = image_reader.Execute()
    image_array = sitk.GetArrayFromImage(dicom_image)

    # Get image properties
    spacing = dicom_image.GetSpacing()
    origin = dicom_image.GetOrigin()
    direction = dicom_image.GetDirection()

    # Initialize a numpy array for the multi-label mask
    mask = np.zeros(sitk.GetArrayFromImage(dicom_image).shape, dtype=np.uint8)

    # Create a dictionary to store ROI label mapping
    roi_label_mapping = {}
    label = 1

    # Assign unique labels to each ROI
    for roi in rtstruct.StructureSetROISequence:
        roi_number = roi.ROINumber
        roi_label_mapping[roi_number] = label
        label += 1

    # Map contours to mask with unique labels
    for contour in rtstruct.ROIContourSequence:
        roi_number = contour.ReferencedROINumber
        roi_label = roi_label_mapping[roi_number]

        for contour_sequence in contour.ContourSequence:
            # Convert the contour data to numpy array
            contour_data = np.array(contour_sequence.ContourData).reshape(-1, 3)

            # Convert contour points to image indices
            contour_points = np.round((contour_data - origin) / spacing).astype(int)

            # Get the slice number
            slice_number = int(contour_points[0, 2])

            # Create a 2D mask for the contour
            slice_mask = np.zeros(mask[slice_number].shape, dtype=np.uint8)
            points = contour_points[:, :2]

            # Draw the contour on the mask
            cv2.fillPoly(slice_mask, [points], roi_label)

            # Add the contour to the mask, preserving labels
            mask[slice_number] = np.maximum(mask[slice_number], slice_mask)

    # Convert the mask to NIfTI
    mask_image = sitk.GetImageFromArray(mask)
    mask_image.SetSpacing(spacing)
    mask_image.SetOrigin(origin)
    mask_image.SetDirection(direction)

    seg_array = sitk.GetArrayFromImage(mask_image)

    # Generate random colors for each segment label
    segment_colors = {}
    for seg_class in np.unique(seg_array):
        if seg_class == 0:
            continue
        color = [randint(0, 255), randint(0, 255), randint(0, 255)]
        segment_colors[seg_class] = {"color": color}

    return image_array, seg_array, segment_colors


if __name__ == "__main__":
    thumbnail_size = int(getenv("SIZE", "300"))
    thread_count = int(getenv("THREADS", "3"))

    workflow_dir = getenv("WORKFLOW_DIR", "None")
    workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
    assert workflow_dir is not None

    batch_name = getenv("BATCH_NAME", "None")
    batch_name = batch_name if batch_name.lower() != "none" else None
    assert batch_name is not None

    operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
    operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
    assert operator_in_dir is not None

    org_image_input_dir = getenv("ORIG_IMAGE_OPERATOR_DIR", "None")
    org_image_input_dir = (
        org_image_input_dir if org_image_input_dir.lower() != "none" else None
    )
    assert org_image_input_dir is not None

    operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
    operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
    assert operator_out_dir is not None

    logger.info("Starting thumbnail generation")

    logger.info(f"thumbnail_size: {thumbnail_size}")
    logger.info(f"thread_count: {thread_count}")
    logger.info(f"workflow_dir: {workflow_dir}")
    logger.info(f"batch_name: {batch_name}")
    logger.info(f"operator_in_dir: {operator_in_dir}")
    logger.info(f"operator_out_dir: {operator_out_dir}")
    logger.info(f"org_image_input_dir: {org_image_input_dir}")

    logger.info("Starting processing on BATCH-ELEMENT-level ...")

    queue = []
    batch_folders = sorted([f for f in glob(join("/", workflow_dir, batch_name, "*"))])
    for batch_element_dir in batch_folders:

        logger.info(f"Processing batch-element {batch_element_dir}")

        seg_element_input_dir = join(batch_element_dir, operator_in_dir)
        orig_element_input_dir = join(batch_element_dir, org_image_input_dir)
        element_output_dir = join(batch_element_dir, operator_out_dir)

        # check if input dir present
        if not exists(seg_element_input_dir):
            logger.warning(f"Input-dir: {seg_element_input_dir} does not exists!")
            logger.warning("-> skipping")
            continue

        queue.append(
            (seg_element_input_dir, orig_element_input_dir, element_output_dir)
        )

    with ThreadPool(thread_count) as threadpool:
        results = threadpool.imap_unordered(create_thumbnail, queue)
        for result, input_file in results:
            logger.info(f"Done: {input_file}")
            if not result:
                exit(1)

    logger.info("BATCH-ELEMENT-level processing done.")

    if processed_count == 0:
        queue = []

        logger.warning("No files have been processed so far!")
        logger.warning("Starting processing on BATCH-LEVEL ...")

        batch_input_dir = join("/", workflow_dir, operator_in_dir)
        batch_org_image_input = join("/", workflow_dir, org_image_input_dir)
        batch_output_dir = join("/", workflow_dir, operator_in_dir)

        # check if input dir present
        if not exists(batch_input_dir):
            logger.warning(f"Input-dir: {batch_input_dir} does not exists!")
            logger.warning("# -> skipping")
        else:
            # creating output dir
            Path(batch_output_dir).mkdir(parents=True, exist_ok=True)

        queue.append((batch_input_dir, batch_org_image_input, batch_output_dir))

        with ThreadPool(thread_count) as threadpool:
            results = threadpool.imap_unordered(create_thumbnail, queue)
            for result, input_file in results:
                logger.info(f"Done: {input_file}")

        logger.info("BATCH-LEVEL-level processing done.")

    if processed_count == 0:
        logger.error("No files have been processed!")
        raise Exception("No files have been processed!")
    else:
        logger.info(f"{processed_count} files have been processed!")
