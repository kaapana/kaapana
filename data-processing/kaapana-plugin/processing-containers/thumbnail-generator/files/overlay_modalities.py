import os
from pathlib import Path
from random import randint

import cv2
import numpy as np
import pydicom
import pydicom_seg
import SimpleITK as sitk
from colormath.color_conversions import convert_color
from colormath.color_objects import LabColor, sRGBColor
from kaapanapy.logger import get_logger
from PIL import Image, ImageFilter
from pydantic import BaseModel

logger = get_logger(__name__)


class Slice(BaseModel):
    slice_index: int
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


def resample_to_reference_image(
    ref_image: sitk.Image, segmentation: sitk.Image
) -> sitk.Image:
    """Resamples a segmentation to match the size and spacing of a reference image

    Args:
        image (sitk.Image): Reference image
        segmentation (sitk.Image): DICOM Segmentation object

    Returns:
        tuple: Tuple containing the cropped image and segmentation
    """

    # Resample segmentation to match the reference image
    resample = sitk.ResampleImageFilter()
    resample.SetReferenceImage(ref_image)
    resample.SetInterpolator(sitk.sitkNearestNeighbor)
    resample.SetDefaultPixelValue(0)
    resample.SetOutputPixelType(segmentation.GetPixelID())
    segmentation_resampled = resample.Execute(segmentation)

    # Check if the resampled segmentation has the same size as the reference image
    assert (
        ref_image.GetSize() == segmentation_resampled.GetSize()
    ), f"Image and segmentation have different sizes: Image: {ref_image.GetSize()}, Segmentation: {segmentation_resampled.GetSize()}"

    return ref_image, segmentation_resampled


def generate_segmentation_thumbnail(
    operator_in_dir: Path, operator_ref_dir: Path, thumbnail_size: int
) -> Image:
    """
    Generate a thumbnail image for a DICOM SEG-based segmentation.

    This function loads the reference DICOM series and the corresponding DICOM SEG segmentation,
    identifies the most relevant slice, and overlays the segmentation on the selected slice
    to generate a visually informative thumbnail.

    Args:
        operator_in_dir (str): Path to the directory containing the DICOM SEG file.
        operator_ref_dir (str): Path to the directory containing the reference DICOM series.

    Returns:
        Image: A PIL Image object representing the thumbnail with segmentation overlay.
    """
    image_array, seg_arrays, segment_colors = load_ref_series_and_segmentation(
        operator_ref_dir, operator_in_dir
    )
    thumbnail = overlay_thumbnail(image_array, seg_arrays, segment_colors)
    return thumbnail


def load_ref_series_and_segmentation(image_dir: str, seg_dir: str) -> tuple:
    """
    Load a DICOM image series and its corresponding segmentation from a DICOM SEG file.

    This function reads a series of DICOM images (3D volume) from `image_dir` and a DICOM SEG
    segmentation file from `seg_dir`. It extracts segmentation masks for each segment class
    and assigns colors to each segment.

    - Uses `pydicom_seg` to parse segmentation masks directly from the DICOM SEG file.
    - Ensures segmentation masks align with the reference DICOM image by resampling if needed.
    - Extracts recommended colors from the segmentation metadata (CIELab or RGB),
      falling back to random colors if unavailable.

    Args:
        image_dir (str): Directory containing the DICOM image series.
        seg_dir (str): Directory containing the DICOM SEG file.

    Returns:
        tuple:
            - image_array (numpy.ndarray): 3D array representing the DICOM image series.
            - seg_arrays (numpy.ndarray): 4D array containing segmentation masks for different segment classes.
            - segment_colors (dict): Dictionary mapping segment classes to RGB color values.
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

    # Read the segmentation
    reader = pydicom_seg.SegmentReader()
    result = reader.read(dicom_seg)

    # Iterate through the segments and extract the colors
    segment_colors = {}
    seg_arrays = []
    for segment_number in result.available_segments:
        seg_array = result.segment_data(segment_number)

        # Check segmentation and image dimensions
        if image_array.shape != seg_array.shape:

            cropped_image, cropped_seg = resample_to_reference_image(
                ref_image=dicom_image, segmentation=result.segment_image(segment_number)
            )
            image_array = sitk.GetArrayFromImage(cropped_image)
            seg_array = sitk.GetArrayFromImage(cropped_seg)

            del cropped_image
            del cropped_seg

        seg_arrays.append(seg_array)
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

    return image_array, np.array(seg_arrays), segment_colors


def overlay_thumbnail(image_array, seg_arrays, segment_colors) -> Image.Image:
    """
    Create a thumbnail by overlaying a DICOM segmentation on the most representative slice.

    The function identifies the best slice based on segmentation characteristics (number of
    classes and foreground pixel area), applies windowing and normalization, and blends the
    segmentation mask with transparency into the image.

    Args:
        image_array (numpy.ndarray): 3D array representing the DICOM image series.
        seg_arrays (numpy.ndarray): 4D array containing segmentation masks for different
                                    segment classes.
        segment_colors (dict): Dictionary mapping segment classes to RGB color values.

    Returns:
        Image: A PIL Image object with the overlaid segmentation.
    """
    # Count the number of classes in each slice
    classes_per_slice = np.sum(
        np.any(seg_arrays > 0, axis=(2, 3)), axis=0
    )  # Shape: (114,)

    # Calculate the total segmentation area for each slice
    area_per_slice = np.sum(
        np.sum(seg_arrays, axis=0) > 0, axis=(1, 2)
    )  # Shape: (114,)

    # Combine the classes and area into a structured array for sorting
    slice_metrics = np.array(
        [
            (i, classes_per_slice[i], area_per_slice[i])
            for i in range(seg_arrays.shape[1])
        ],
        dtype=[("index", int), ("num_classes", int), ("area", int)],
    )

    # Sort by number of classes (descending) and area (descending)
    sorted_slices = np.sort(slice_metrics, order=["num_classes", "area"])[::-1]

    # The slice with the most classes and largest area
    best_slice_index = sorted_slices[0]["index"]
    best_slice_num_classes = sorted_slices[0]["num_classes"]
    best_slice_area = sorted_slices[0]["area"]

    best_slice = Slice(
        slice_index=best_slice_index,
        number_of_classes=best_slice_num_classes,
        number_of_foreground_pixels=best_slice_area,
    )

    logger.info(
        f"Best slice: {best_slice.slice_index} with {best_slice.number_of_classes} classes and {best_slice.number_of_foreground_pixels} foreground pixels"
    )

    # Select the best image slice
    base_image_array = image_array[best_slice.slice_index, :, :]
    del image_array

    # Binary mask to highligh where the segments are
    seg_array_binary = np.where(np.sum(seg_arrays, axis=0) > 0, 1, 0)

    # Select the corresponding binary mask
    base_seg_array_binary = seg_array_binary[best_slice.slice_index, :, :]
    del seg_array_binary

    # Use the binary mask to get the relevant intensities (To see the regions within the mask better)
    masked_array = base_image_array * base_seg_array_binary

    # Areas with intensity values over 0
    areas_over_zero = masked_array[masked_array > 0]

    # Calculate the min intensity for the windowing
    min_intensity = np.min(areas_over_zero)

    # Calculate the max intensity for the windowing. Use the mean intensity plus 2 standard deviations
    max_intensity = np.mean(areas_over_zero) + 2 * np.std(areas_over_zero)

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

    # Create an RGBA image
    image = Image.fromarray(normalized_data).convert("RGBA")

    # Combine all binary masks for the best slice to calculate overlap
    overlap_map = np.sum(
        seg_arrays[:, best_slice_index], axis=0
    )  # Shape: (height, width)

    # Avoid division by zero
    overlap_map = np.clip(overlap_map, 1, None)

    # Apply transparency blending for each segment
    for seg_class in range(seg_arrays.shape[0]):
        try:
            color = segment_colors[seg_class + 1][
                "color"
            ]  # RGB tuple (e.g., (255, 0, 0))
        except KeyError:
            logger.warning(
                f"Color not found for segment {seg_class + 1}. Using random color."
            )
            color = [randint(0, 255), randint(0, 255), randint(0, 255)]

        mask_array = np.uint8(seg_arrays[seg_class, best_slice_index] > 0) * 255

        mask = Image.fromarray(mask_array, mode="L")

        # Draw the border with full opacity
        border_overlay = Image.new("RGBA", image.size, tuple(color) + (255,))
        image = Image.composite(
            border_overlay, image, mask.filter(ImageFilter.FIND_EDGES)
        )

        # Calculate normalized opacity for this segment
        normalized_opacity = 128 / overlap_map  # Scale total overlap to 50% max
        normalized_opacity_map = (mask_array / 255 * normalized_opacity).astype(
            np.uint8
        )

        # Convert normalized opacity to a PIL image
        mask_image = Image.fromarray(normalized_opacity_map, mode="L")

        # Draw the inner part with calculated opacity
        fill_overlay = Image.new("RGBA", image.size, tuple(color) + (0,))
        fill_overlay.putalpha(
            mask_image
        )  # Use mask_image directly as the alpha channel

        image = Image.alpha_composite(image, fill_overlay)

    return image


def generate_rtstruct_thumbnail(
    operator_in_dir: Path, operator_ref_dir: Path, thumbnail_size: int
) -> Image.Image:
    """
    Generate a thumbnail image for an RTSTRUCT-based DICOM segmentation.

    This function loads the reference DICOM series and RTSTRUCT segmentation, identifies the
    most relevant slice, and overlays the segmentation on the selected slice to generate a
    visually informative thumbnail.

    Args:
        dcm_incoming_dir (str): Path to the directory containing the RTSTRUCT DICOM file.
        dcm_ref_dir (str): Path to the directory containing the reference DICOM series.

    Returns:
        Image: A PIL Image object representing the thumbnail with segmentation overlay.
    """
    image_array, seg_arrays, segment_colors = load_ref_image_and_rtstruct(
        operator_ref_dir, operator_in_dir
    )
    thumbnail = overlay_thumbnail(image_array, seg_arrays, segment_colors)
    return thumbnail


def load_ref_image_and_rtstruct(image_dir: str, rt_struct_dir: str) -> tuple:
    """
    Load a DICOM image series and its corresponding segmentation from an RTSTRUCT file.

    RTSTRUCT segmentation stores contours rather than pixel-based segmentation.
    This function extracts the contours, rasterizes them into a 3D segmentation
    mask, and assigns unique labels to each ROI.

    Key Differences & Specifics:
    - RTSTRUCT files contain **contour-based** segmentation instead of voxel-based masks.
    - Each ROI (Region of Interest) is assigned a **unique integer label** to differentiate
      segment classes.
    - Converts contour data into a **binary mask** by rasterizing each slice using OpenCV.
    - Uses the DICOM image's **spacing, origin, and direction** for proper alignment.
    - Assigns **random colors** to each segment since RTSTRUCT files do not contain color metadata.

    Args:
        image_dir (str): Directory containing the DICOM image series.
        rt_struct_dir (str): Directory containing the RTSTRUCT file.

    Returns:
        tuple:
            - image_array (numpy.ndarray): 3D array representing the DICOM image series.
            - seg_arrays (numpy.ndarray): 4D array where each slice contains rasterized segment contours.
            - segment_colors (dict): Dictionary mapping segment classes to randomly generated colors.
    """
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

    # Convert seg_array to a 4D array (num_classes, num_slices, height, width)
    unique_classes = np.unique(seg_array)
    seg_arrays = np.array(
        [
            (seg_array == class_value).astype(np.uint8)
            for class_value in unique_classes
            if class_value != 0
        ]
    )  # Shape: (num_classes, num_slices, height, width)

    # Generate random colors for each segment label
    segment_colors = {}
    for seg_class in np.unique(seg_array):
        if seg_class == 0:
            continue
        color = [randint(0, 255), randint(0, 255), randint(0, 255)]
        segment_colors[seg_class] = {"color": color}

    return image_array, seg_arrays, segment_colors
