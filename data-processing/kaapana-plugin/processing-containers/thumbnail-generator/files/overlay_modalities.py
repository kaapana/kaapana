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
import warnings

logger = get_logger(__name__)


class Slice(BaseModel):
    slice_index: int
    number_of_classes: int
    number_of_foreground_pixels: int


def create_empty_ref_series(operator_ref_dir: Path, operator_in_dir: Path):
    """
    Create a dummy CT reference series matching the geometry of an incoming DICOM SEG.

    Some SEG objects reference a source series that is not available at import time. This function
    creates a synthetic CT series (one slice per referenced frame) using geometry information from
    the SEG metadata (rows/cols, spacing, orientation, slice positions).

    The pixel data is constant and carries no diagnostic meaning; it is intended only as geometry scaffolding.

    Args:
        operator_ref_dir (Path): Output directory where the dummy reference DICOM slices are written.
        operator_in_dir (Path): Directory containing the DICOM SEG file used to derive geometry.
    """
    file_name = os.path.join(operator_in_dir, os.listdir(operator_in_dir)[0])
    # Read the segmentation
    seg_ds = pydicom.dcmread(file_name)

    # SEG references to source image slices
    try:
        ref_series = seg_ds.ReferencedSeriesSequence[0].ReferencedInstanceSequence
    except Exception as e:
        raise ValueError(
            f"SEG has no ReferencedSeriesSequence/ReferencedInstanceSequence: {file_name}"
        ) from e
    num_slices = len(ref_series)

    # Extract info from the SEG
    rows = seg_ds.Rows
    cols = seg_ds.Columns
    spacing = [
        float(x)
        for x in seg_ds.SharedFunctionalGroupsSequence[0]
        .PixelMeasuresSequence[0]
        .PixelSpacing
    ]
    spacing_z = float(
        seg_ds.SharedFunctionalGroupsSequence[0].PixelMeasuresSequence[0].SliceThickness
    )
    orientation = (
        seg_ds.SharedFunctionalGroupsSequence[0]
        .PlaneOrientationSequence[0]
        .ImageOrientationPatient
    )
    position = (
        seg_ds.PerFrameFunctionalGroupsSequence[0]
        .PlanePositionSequence[0]
        .ImagePositionPatient
    )

    # Create one slice per referenced frame
    SeriesInstanceUID = pydicom.uid.generate_uid()

    for i in range(num_slices):
        file_meta = pydicom.dataset.FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = pydicom.uid.CTImageStorage
        file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
        file_meta.ImplementationClassUID = pydicom.uid.generate_uid()
        file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian

        ds = pydicom.dataset.FileDataset(
            f"{file_meta.MediaStorageSOPInstanceUID}.dcm",
            {},
            file_meta=file_meta,
            preamble=b"\0" * 128,
        )

        # Set CT metadata
        ds.PatientName = "Dummy^CT"
        ds.PatientID = "000000"
        ds.Modality = "CT"
        ds.SeriesInstanceUID = SeriesInstanceUID
        ds.StudyInstanceUID = seg_ds.StudyInstanceUID
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
        ds.InstanceNumber = i + 1
        ds.ImagePositionPatient = [
            float(position[0]),
            float(position[1]),
            float(position[2] + i * spacing_z),
        ]
        ds.ImageOrientationPatient = orientation
        ds.Rows = rows
        ds.Columns = cols
        ds.PixelSpacing = spacing
        ds.SliceThickness = spacing_z
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 1  # signed
        ds.RescaleIntercept = 1
        ds.RescaleSlope = 1
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.is_little_endian = True
        ds.is_implicit_VR = False

        # Create constant pixel data (no diagnostic meaning; geometry scaffolding only)
        pixel_array = np.ones((rows, cols), dtype=np.int16)
        ds.PixelData = pixel_array.tobytes()

        # Save to disk
        ds.save_as(
            os.path.join(
                operator_ref_dir, f"{file_meta.MediaStorageSOPInstanceUID}.dcm"
            )
        )


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


def _extract_segment_colors_from_dicom_seg(dicom_seg) -> dict:
    segment_colors = {}
    if not hasattr(dicom_seg, "SegmentSequence"):
        return segment_colors

    for seg in dicom_seg.SegmentSequence:
        seg_num = int(seg.SegmentNumber)
        seg_label = getattr(seg, "SegmentLabel", str(seg_num))

        if hasattr(seg, "RecommendedDisplayCIELabValue"):
            cie_lab_color_int = seg.RecommendedDisplayCIELabValue
            cie_lab_color_float = [float(int(x)) for x in cie_lab_color_int]
            lab_vals = dicomlab2LAB(dicomlab=cie_lab_color_float)
            lab = LabColor(lab_vals[0], lab_vals[1], lab_vals[2])
            rgb = convert_color(lab, sRGBColor).get_upscaled_value_tuple()
            color = [max(min(int(x), 255), 0) for x in rgb]
            color_type = "CIELab"
        elif hasattr(seg, "RecommendedDisplayRGBValue"):
            color = [int(x) for x in seg.RecommendedDisplayRGBValue]
            color_type = "RGB"
        else:
            color = [randint(0, 255), randint(0, 255), randint(0, 255)]
            color_type = "Random"

        segment_colors[seg_num] = {
            "label": seg_label,
            "color_type": color_type,
            "color": color,
        }

    return segment_colors


def _ref_paths_from_seg(image_dir: str, seg_ds: pydicom.Dataset) -> list[str]:
    """
    Build an ordered list of reference slice file paths from a DICOM SEG's references.

    The SEG references its source instances via ReferencedSOPInstanceUIDs. We resolve those UIDs
    to local files using the convention "<SOPInstanceUID>.dcm" in `image_dir` and preserve the
    reference order as given in the SEG (frame order).

    Args:
        image_dir (str): Directory that contains the referenced DICOM instances.
        seg_ds (pydicom.Dataset): The DICOM SEG dataset holding the reference list.

    Returns:
        list[str]: Ordered file paths to referenced instances that exist locally. Empty if unresolved.
    """
    try:
        refs = seg_ds.ReferencedSeriesSequence[0].ReferencedInstanceSequence
    except Exception:
        return []

    paths: list[str] = []
    for ref in refs:
        uid = str(ref.ReferencedSOPInstanceUID)
        p = os.path.join(image_dir, f"{uid}.dcm")
        if os.path.exists(p):
            paths.append(p)

    return paths


def _pick_best_slice_index(
    classes_per_slice: np.ndarray, area_per_slice: np.ndarray
) -> int:
    # lexsort sorts ascending; we want the maximum (classes, then area)
    return int(np.lexsort((area_per_slice, classes_per_slice))[-1])


def _overlay_from_2d_masks(
    base_slice: np.ndarray,
    masks_2d: list[tuple[int, np.ndarray]],
    overlap_map: np.ndarray,
    segment_colors: dict,
    thumbnail_size: int,
) -> Image.Image:
    """
    Render an overlay thumbnail from 2D segment masks.

    The overlay matches the legacy style:
      - solid borders (edge filter)
      - semi-transparent fills with opacity normalized by the number of overlapping segments

    Intensity windowing is computed from the pixels under the union of all masks and uses a
    percentile-based window (2nd–98th percentile) for robust contrast across different scanners.

    Args:
        base_slice (np.ndarray): 2D image slice (y, x).
        masks_2d (list[tuple[int, np.ndarray]]): List of (segment_id, 2D mask) pairs for the slice.
        overlap_map (np.ndarray): 2D map counting how many segments overlap per pixel.
        segment_colors (dict): Mapping from segment_id to display color metadata.
        thumbnail_size (int): Maximum size (pixels) of the thumbnail (largest side).

    Returns:
        Image.Image: RGBA thumbnail image with overlay.
    """
    base = base_slice.astype(np.float32)

    # union mask for windowing
    union = overlap_map > 0
    vals = base[union]

    # Robust windowing fallback
    if vals.size == 0:
        vals = base.ravel()

    vals_pos = vals[vals > 0]
    vals_for_stats = vals_pos if vals_pos.size > 0 else vals

    # Percentile-based windowing is much more stable than mean±std for odd distributions
    p_low, p_high = np.percentile(vals_for_stats, [2.0, 98.0])

    # Expand slightly to avoid overly tight contrast
    margin = 0.05 * (p_high - p_low)
    window_min = float(p_low - margin)
    window_max = float(p_high + margin)

    # Clamp to actual slice range (prevents nonsense windows)
    base_min = float(np.min(base))
    base_max = float(np.max(base))
    window_min = max(window_min, base_min)
    window_max = min(window_max, base_max)

    # Final safety: ensure strictly increasing window
    if window_max <= window_min:
        window_min, window_max = base_min, base_max
        if window_max <= window_min:
            window_max = window_min + 1.0

    windowed = np.clip(base, window_min, window_max)
    denom = (window_max - window_min) if (window_max - window_min) != 0 else 1.0
    normalized = ((windowed - window_min) / denom * 255.0).astype(np.uint8)

    image = Image.fromarray(normalized).convert("RGBA")

    overlap_map = np.clip(overlap_map.astype(np.float32), 1.0, None)

    for seg_id, mask2d in masks_2d:
        info = segment_colors.get(seg_id, {})
        color = info.get("color") or [randint(0, 255), randint(0, 255), randint(0, 255)]

        mask_array = mask2d.astype(np.uint8) * 255
        mask = Image.fromarray(mask_array, mode="L")

        # Border
        border_overlay = Image.new("RGBA", image.size, tuple(color) + (255,))
        image = Image.composite(
            border_overlay, image, mask.filter(ImageFilter.FIND_EDGES)
        )

        # Fill with normalized opacity
        normalized_opacity = 128.0 / overlap_map
        alpha = (mask_array / 255.0 * normalized_opacity).astype(np.uint8)
        alpha_img = Image.fromarray(alpha, mode="L")

        fill_overlay = Image.new("RGBA", image.size, tuple(color) + (0,))
        fill_overlay.putalpha(alpha_img)
        image = Image.alpha_composite(image, fill_overlay)

    image.thumbnail((thumbnail_size, thumbnail_size))
    return image


def _thumbnail_from_labelmap(
    image_array: np.ndarray,
    labelmap: np.ndarray,
    segment_colors: dict,
    thumbnail_size: int,
) -> Image.Image:
    z = labelmap.shape[0]

    area_per_slice = np.count_nonzero(labelmap, axis=(1, 2)).astype(np.int64)
    classes_per_slice = np.zeros(z, dtype=np.int16)
    for i in range(z):
        u = np.unique(labelmap[i])
        classes_per_slice[i] = len(u) - (1 if 0 in u else 0)

    best_slice = _pick_best_slice_index(classes_per_slice, area_per_slice)

    base_slice = image_array[best_slice].copy()
    slice_labels = np.unique(labelmap[best_slice])
    slice_labels = slice_labels[slice_labels != 0]

    masks_2d = []
    overlap_map = np.zeros(labelmap[0].shape, dtype=np.uint16)
    for lbl in slice_labels:
        m2 = labelmap[best_slice] == lbl
        masks_2d.append((int(lbl), m2))
        overlap_map += m2.astype(np.uint16)

    return _overlay_from_2d_masks(
        base_slice=base_slice,
        masks_2d=masks_2d,
        overlap_map=overlap_map,
        segment_colors=segment_colors,
        thumbnail_size=thumbnail_size,
    )


def _same_geometry(a: sitk.Image, b: sitk.Image) -> bool:
    return (
        a.GetSize() == b.GetSize()
        and a.GetSpacing() == b.GetSpacing()
        and a.GetOrigin() == b.GetOrigin()
        and a.GetDirection() == b.GetDirection()
    )


def _extract_ref_slice_zyx(ref_img: sitk.Image, slice_idx: int) -> np.ndarray:
    """
    Extract a single z-slice from a 3D SimpleITK image as a 2D numpy array (y, x).
    SimpleITK indexing is (x, y, z).
    """
    sx, sy, sz = ref_img.GetSize()
    slice_idx = int(np.clip(slice_idx, 0, sz - 1))

    slice_img = sitk.Extract(ref_img, (sx, sy, 0), (0, 0, slice_idx))
    arr = sitk.GetArrayFromImage(slice_img)  # typically shape (1, y, x)
    return arr[0] if arr.ndim == 3 else arr


def _first_dicom_file(folder: str) -> str:
    files = sorted(
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(".dcm")
    )
    if not files:
        raise FileNotFoundError(f"No .dcm files found in {folder}")
    return files[0]


def resample_to_reference_image(
    ref_image: sitk.Image, segmentation: sitk.Image
) -> sitk.Image:
    """
    Resample a segmentation image to match a reference image geometry.

    Uses nearest-neighbor interpolation to preserve label values.

    Args:
        ref_image (sitk.Image): Reference image defining target geometry (size, spacing, origin, direction).
        segmentation (sitk.Image): Segmentation image to resample into the reference geometry.

    Returns:
        sitk.Image: The segmentation resampled to the reference image geometry.
    """

    # Resample segmentation to match the reference image
    resample = sitk.ResampleImageFilter()
    resample.SetReferenceImage(ref_image)
    resample.SetInterpolator(sitk.sitkNearestNeighbor)
    resample.SetDefaultPixelValue(0)
    resample.SetOutputPixelType(segmentation.GetPixelID())
    segmentation_resampled = resample.Execute(segmentation)

    # Check if the resampled segmentation has the same size as the reference image
    if ref_image.GetSize() != segmentation_resampled.GetSize():
        raise ValueError(
            f"Image and segmentation have different sizes: "
            f"Image: {ref_image.GetSize()}, Segmentation: {segmentation_resampled.GetSize()}"
        )

    return segmentation_resampled


def generate_segmentation_thumbnail(
    operator_in_dir: Path,
    operator_ref_dir: Path,
    thumbnail_size: int,
    candidate_slices_count: int = 12,
) -> Image.Image:
    """
    Generate an overlay thumbnail for a DICOM SEG object.

    Loads the reference DICOM series and the DICOM SEG, selects a representative slice, and renders
    the segmentation overlay on that slice.

    Slice selection is designed to be memory-bounded:
      1) Compute per-slice class counts exactly and an approximate area score (sum of per-segment areas).
      2) Select the top-N candidate slices by (class count, approx area) and compute the exact union
         foreground area only for those candidates.
      3) Render only 2D masks for the final selected slice.

    Args:
        operator_in_dir (Path): Directory containing the DICOM SEG file.
        operator_ref_dir (Path): Directory containing the referenced DICOM image series.
        thumbnail_size (int): Maximum size (pixels) of the thumbnail (largest side).
        candidate_slices_count (int): Number of candidate slices to evaluate with exact union area.
            Higher values more closely match the true global optimum but require more CPU.

    Returns:
        Image: A PIL Image object representing the selected slice with segmentation overlay.
    """
    dicom_image, result, segment_colors = load_ref_series_and_segmentation(
        str(operator_ref_dir), str(operator_in_dir)
    )

    # SimpleITK size is (x, y, z) -> we want numpy-style (z, y, x)
    sx, sy, sz = dicom_image.GetSize()
    target_shape = (sz, sy, sx)
    z, h, w = target_shape

    # ---------- PASS 1: cheap metrics (exact classes, approximate area) ----------
    classes_per_slice = np.zeros(z, dtype=np.int16)
    area_sum_per_slice = np.zeros(
        z, dtype=np.int64
    )  # sum of per-segment areas (overcounts overlaps)

    segments = [int(s) for s in sorted(result.available_segments)]

    seg_needs_resample: dict[int, bool] = {}
    for seg_num in segments:
        seg_img = result.segment_image(seg_num)
        seg_needs_resample[int(seg_num)] = not _same_geometry(seg_img, dicom_image)

    for seg_num in sorted(result.available_segments):
        if seg_needs_resample[int(seg_num)]:
            seg_rs = resample_to_reference_image(
                ref_image=dicom_image,
                segmentation=result.segment_image(seg_num),
            )
            seg_arr = sitk.GetArrayFromImage(seg_rs)
            del seg_rs
        else:
            seg_arr = result.segment_data(seg_num)

        present = np.any(seg_arr, axis=(1, 2))
        classes_per_slice += present.astype(np.int16)

        # counts non-zero pixels per slice (works for 0/1 masks and label-like masks)
        area_sum_per_slice += np.count_nonzero(seg_arr, axis=(1, 2)).astype(np.int64)

        del seg_arr, present

    # Pick top-M candidate slices by (classes, approx area)
    candidate_count = max(1, min(candidate_slices_count, z))
    candidate_slices = np.lexsort((area_sum_per_slice, classes_per_slice))[
        -candidate_count:
    ]
    candidate_slices = np.sort(candidate_slices)  # helps stable behavior

    # ---------- PASS 2: exact union area for candidates only ----------
    # Preallocate memory
    tmp = np.empty((candidate_slices.size, h, w), dtype=bool)
    # union_candidates shape: (M, h, w)
    union_candidates = np.zeros((candidate_slices.size, h, w), dtype=bool)

    for seg_num in segments:
        if seg_needs_resample[int(seg_num)]:
            seg_rs = resample_to_reference_image(
                ref_image=dicom_image,
                segmentation=result.segment_image(seg_num),
            )
            seg_arr = sitk.GetArrayFromImage(seg_rs)
            del seg_rs
        else:
            seg_arr = result.segment_data(seg_num)

        # Only touch candidate slices -> (M, h, w)
        # No allocation only filling in
        np.greater(seg_arr[candidate_slices], 0, out=tmp)
        np.logical_or(union_candidates, tmp, out=union_candidates)

        del seg_arr

    area_exact_candidates = np.sum(union_candidates, axis=(1, 2)).astype(np.int64)
    del union_candidates

    # Final best slice using same ordering as before:
    # (classes_per_slice, then exact union area)
    best_idx = int(
        np.lexsort((area_exact_candidates, classes_per_slice[candidate_slices]))[-1]
    )
    best_slice = int(candidate_slices[best_idx])
    best_area = int(area_exact_candidates[best_idx])

    logger.info(
        f"Best slice: {best_slice} with {int(classes_per_slice[best_slice])} classes "
        f"and {best_area} foreground pixels (exact union, candidates={candidate_count})"
    )

    # Extract only the chosen slice (avoid a full numpy copy of the ref volume)
    base_slice = _extract_ref_slice_zyx(dicom_image, best_slice).copy()

    # ---------- PASS 3: collect 2D masks only for the chosen slice ----------
    masks_2d = []
    overlap_map = np.zeros((h, w), dtype=np.uint16)

    for seg_num in segments:
        if seg_needs_resample[int(seg_num)]:
            seg_rs = resample_to_reference_image(
                ref_image=dicom_image,
                segmentation=result.segment_image(seg_num),
            )
            seg_arr = sitk.GetArrayFromImage(seg_rs)
            del seg_rs
        else:
            seg_arr = result.segment_data(seg_num)

        m2 = seg_arr[best_slice] > 0
        if m2.any():
            masks_2d.append((int(seg_num), m2))
            overlap_map += m2.astype(np.uint16)

        del seg_arr, m2

    return _overlay_from_2d_masks(
        base_slice=base_slice,
        masks_2d=masks_2d,
        overlap_map=overlap_map,
        segment_colors=segment_colors,
        thumbnail_size=thumbnail_size,
    )


def load_ref_series_and_segmentation(image_dir: str, seg_dir: str) -> tuple:
    """
    Load a referenced DICOM image series and its corresponding DICOM SEG.

    The reference series is loaded using the SOPInstanceUIDs listed in the SEG's
    ReferencedSeriesSequence when possible. This avoids ITK/SimpleITK "size mismatch" failures
    when the reference directory contains mixed instances (e.g., scout + diagnostic images).

    Args:
        image_dir (str): Directory containing the referenced DICOM image series.
        seg_dir (str): Directory containing a DICOM SEG file.

    Returns:
        tuple:
            - dicom_image (sitk.Image): Reference series as a SimpleITK image.
            - result (pydicom_seg.reader.SegmentReadResult): Parsed SEG result used to access per-segment data.
            - segment_colors (dict): Mapping {segment_number: {"label": str, "color_type": str, "color": [r,g,b]}}.
    """
    # Load the segmentation first (we may use it to determine the correct reference slices)
    file_name = _first_dicom_file(seg_dir)
    dicom_seg = pydicom.dcmread(file_name)

    reader = pydicom_seg.SegmentReader()
    result = reader.read(dicom_seg)
    segment_colors = _extract_segment_colors_from_dicom_seg(dicom_seg)

    # Load the image
    image_reader = sitk.ImageSeriesReader()

    # Preferred: use the SEG's referenced SOPInstanceUIDs to avoid mixed-size series issues
    ref_paths = _ref_paths_from_seg(image_dir, dicom_seg)
    if ref_paths:
        logger.info(
            f"Using {len(ref_paths)} referenced instances from SEG to load reference series"
        )
        image_reader.SetFileNames(ref_paths)
    else:
        # Fallback: use the series finder (may include mixed instances if directory is polluted)
        dicom_names = image_reader.GetGDCMSeriesFileNames(image_dir)
        logger.info(f"Found {len(dicom_names)} DICOM files (fallback scan)")
        image_reader.SetFileNames(dicom_names)

    try:
        dicom_image = image_reader.Execute()
    except Exception as e:
        raise RuntimeError(
            f"Failed to load reference series from {image_dir}. "
            f"ref_paths={len(ref_paths)} seg_file={file_name}"
        ) from e

    return dicom_image, result, segment_colors


def overlay_thumbnail(image_array, seg_arrays, segment_colors) -> Image.Image:
    """
    Deprecated: Create a thumbnail by overlaying a DICOM segmentation on the most representative slice.

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
    warnings.warn(
        "overlay_thumbnail() is deprecated; use generate_segmentation_thumbnail() or generate_rtstruct_thumbnail().",
        DeprecationWarning,
        stacklevel=2,
    )
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
        operator_in_dir (Path): Directory containing the RTSTRUCT DICOM file.
        operator_ref_dir (Path): Directory containing the referenced DICOM image series.
        thumbnail_size (int): Maximum size (pixels) of the thumbnail (largest side).

    Returns:
        Image.Image: A PIL Image object representing the selected slice with RTSTRUCT overlay.
    """
    image_array, labelmap, segment_colors = load_ref_image_and_rtstruct(
        operator_ref_dir, operator_in_dir
    )
    thumbnail = _thumbnail_from_labelmap(
        image_array, labelmap, segment_colors, thumbnail_size
    )
    return thumbnail


def load_ref_image_and_rtstruct(image_dir: str, rt_struct_dir: str) -> tuple:
    """
    Load a DICOM image series and rasterize an RTSTRUCT into a 3D labelmap.

    RTSTRUCT stores contour points in patient (physical) coordinates. This function converts those
    points into image index space using SimpleITK's physical->continuous-index transform and then
    rasterizes each contour polygon into a per-slice labelmap using OpenCV.

    Notes:
        - Overlapping ROIs are merged by taking the maximum label value per pixel.
        - ROI colors are randomized (RTSTRUCT may contain colors; this implementation does not use them).

    Args:
        image_dir (str): Directory containing the referenced DICOM image series.
        rt_struct_dir (str): Directory containing the RTSTRUCT file.

    Returns:
        tuple:
            - image_array (numpy.ndarray): Reference series as a NumPy array (z, y, x).
            - labelmap (numpy.ndarray): 3D labelmap (z, y, x), background=0, ROI labels >= 1.
            - segment_colors (dict): Mapping {label: {"color": [r,g,b]}} used for rendering.
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

    # Initialize a numpy array for the multi-label mask
    mask = np.zeros(image_array.shape, dtype=np.uint16)

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

            # Convert physical points -> continuous image index (i, j, k)
            # This accounts for origin + spacing + direction (oblique images!)
            idx = np.array(
                [
                    dicom_image.TransformPhysicalPointToContinuousIndex(tuple(p))
                    for p in contour_data
                ],
                dtype=np.float64,
            )

            # Choose slice number robustly: median k-index across all points
            slice_number = int(np.round(np.median(idx[:, 2])))

            # Guard: skip if contour maps outside volume
            if slice_number < 0 or slice_number >= mask.shape[0]:
                continue

            # OpenCV expects points in (x, y) = (i, j), int32, and shaped (N, 1, 2)
            points = np.round(idx[:, :2]).astype(np.int32)

            # Clip to bounds (avoid OpenCV issues if points fall slightly outside)
            points[:, 0] = np.clip(points[:, 0], 0, mask.shape[2] - 1)  # x / i
            points[:, 1] = np.clip(points[:, 1], 0, mask.shape[1] - 1)  # y / j

            poly = points.reshape((-1, 1, 2))

            # Fill polygon into a 2D slice mask
            slice_mask = np.zeros(mask[slice_number].shape, dtype=np.uint16)
            cv2.fillPoly(slice_mask, [poly], int(roi_label))

            # Merge into labelmap (note: overlapping ROIs get resolved by max label)
            mask[slice_number] = np.maximum(mask[slice_number], slice_mask)

    # Instead of building one-hot seg_arrays (4D), keep the 3D labelmap
    labelmap = mask.astype(np.uint16)

    # Generate random colors per label
    segment_colors = {}
    for lbl in np.unique(labelmap):
        if lbl == 0:
            continue
        segment_colors[int(lbl)] = {
            "color": [randint(0, 255), randint(0, 255), randint(0, 255)]
        }

    return image_array, labelmap, segment_colors
