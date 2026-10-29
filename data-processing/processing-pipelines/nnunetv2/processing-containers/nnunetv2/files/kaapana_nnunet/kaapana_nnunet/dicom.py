"""DICOM -> nnU-Net: image series to NIfTI, DICOM SEG and RTSTRUCT to label maps on an image grid.

No guessing: a segmentation whose geometry cannot be placed on its image raises ConversionError.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pydicom
import SimpleITK as sitk

logger = logging.getLogger(__name__)

SEG_MODALITIES = ("SEG", "RTSTRUCT")


class ConversionError(Exception):
    pass


# ---------- image series ----------


def read_image_series(series_dir: Path, with_files: bool = False):
    """The series as a 3D image; with ``with_files`` also the files in slice order (k = 0, 1, ...)."""
    files = sorted(str(p) for p in Path(series_dir).iterdir() if p.is_file())
    if not files:
        raise ConversionError(f"{series_dir} contains no DICOM files")
    names = files
    if len(files) == 1:
        image = sitk.ReadImage(files[0])  # multi-frame object
    else:
        reader = sitk.ImageSeriesReader()
        series_ids = reader.GetGDCMSeriesIDs(str(series_dir))
        if len(series_ids) != 1:
            raise ConversionError(f"{series_dir} contains {len(series_ids)} series, expected exactly one")
        names = reader.GetGDCMSeriesFileNames(str(series_dir), series_ids[0])
        if len(names) != len(files):
            raise ConversionError(
                f"only {len(names)} of {len(files)} files of {series_dir} form one volume "
                "(several stacks, localizers or missing slices?)"
            )
        reader.SetFileNames(names)
        image = reader.Execute()
    if image.GetDimension() != 3:
        raise ConversionError(f"{series_dir} is not a 3D volume (dimension {image.GetDimension()})")
    if image.GetNumberOfComponentsPerPixel() != 1:
        raise ConversionError(f"{series_dir} has {image.GetNumberOfComponentsPerPixel()} components per pixel")
    return (image, list(names)) if with_files else image


def same_geometry(a: sitk.Image, b: sitk.Image, tol: float = 1e-3) -> bool:
    return (
        a.GetSize() == b.GetSize()
        and np.allclose(a.GetSpacing(), b.GetSpacing(), atol=tol)
        and np.allclose(a.GetOrigin(), b.GetOrigin(), atol=tol * 100)
        and np.allclose(a.GetDirection(), b.GetDirection(), atol=tol)
    )


def resample_to(image: sitk.Image, reference: sitk.Image, label: bool = False) -> sitk.Image:
    interpolator = sitk.sitkNearestNeighbor if label else sitk.sitkLinear
    return sitk.Resample(image, reference, sitk.Transform(), interpolator, 0, image.GetPixelID())


def _physical_to_index(reference: sitk.Image, points: np.ndarray) -> np.ndarray:
    """(n, 3) LPS points -> (n, 3) continuous (i, j, k) indices of ``reference``."""
    direction = np.array(reference.GetDirection()).reshape(3, 3)
    spacing = np.array(reference.GetSpacing())
    origin = np.array(reference.GetOrigin())
    return (np.linalg.inv(direction) @ (points - origin).T).T / spacing


# ---------- segmentation objects ----------


def referenced_series_uid(ds: pydicom.Dataset) -> Optional[str]:
    if ds.Modality == "SEG":
        for item in ds.get("ReferencedSeriesSequence", []):
            return item.SeriesInstanceUID
    if ds.Modality == "RTSTRUCT":
        for frame in ds.get("ReferencedFrameOfReferenceSequence", []):
            for study in frame.get("RTReferencedStudySequence", []):
                for series in study.get("RTReferencedSeriesSequence", []):
                    return series.SeriesInstanceUID
    return None


def read_segmentation_object(series_dir: Path) -> pydicom.Dataset:
    files = [p for p in Path(series_dir).iterdir() if p.is_file()]
    if len(files) != 1:
        raise ConversionError(f"{series_dir}: expected one SEG/RTSTRUCT instance, found {len(files)}")
    return pydicom.dcmread(files[0])


def segment_masks(ds: pydicom.Dataset, reference: sitk.Image) -> dict[str, np.ndarray]:
    """{segment name: boolean mask as (z, y, x) array on the reference grid}"""
    if ds.Modality == "SEG":
        return _seg_masks(ds, reference)
    if ds.Modality == "RTSTRUCT":
        return _rtstruct_masks(ds, reference)
    raise ConversionError(f"unsupported modality {ds.Modality}")


def _frame_attr(ds, frame_index, sequence, attr):
    candidates = []
    if "PerFrameFunctionalGroupsSequence" in ds:
        candidates.append(ds.PerFrameFunctionalGroupsSequence[frame_index])
    if "SharedFunctionalGroupsSequence" in ds:
        candidates.append(ds.SharedFunctionalGroupsSequence[0])
    for group in candidates:
        if sequence in group:
            return getattr(group[sequence][0], attr)
    raise ConversionError(f"SEG frame {frame_index} has no {sequence}.{attr}")


def _seg_masks(ds: pydicom.Dataset, reference: sitk.Image) -> dict[str, np.ndarray]:
    seg_type = ds.get("SegmentationType", "BINARY")
    pixels = ds.pixel_array
    if pixels.ndim == 2:
        pixels = pixels[None]
    if seg_type == "FRACTIONAL":
        pixels = pixels > (ds.get("MaximumFractionalValue", 255) / 2)

    names = {int(s.SegmentNumber): str(s.SegmentLabel).strip() for s in ds.SegmentSequence}
    shape = reference.GetSize()[::-1]  # (z, y, x)
    masks = {name: np.zeros(shape, dtype=bool) for name in names.values()}
    ref_dir = np.array(reference.GetDirection()).reshape(3, 3)
    ref_spacing = np.array(reference.GetSpacing())

    for f in range(pixels.shape[0]):
        position = np.array(_frame_attr(ds, f, "PlanePositionSequence", "ImagePositionPatient"), dtype=float)
        orientation = np.array(_frame_attr(ds, f, "PlaneOrientationSequence", "ImageOrientationPatient"), dtype=float)
        spacing = np.array(_frame_attr(ds, f, "PixelMeasuresSequence", "PixelSpacing"), dtype=float)
        # DICOM PixelSpacing is (row spacing, column spacing) = (y, x)
        if not (
            np.allclose(orientation[:3], ref_dir[:, 0], atol=1e-3)
            and np.allclose(orientation[3:], ref_dir[:, 1], atol=1e-3)
            and np.allclose(spacing[::-1], ref_spacing[:2], atol=1e-3)
            and pixels.shape[1:] == shape[1:]
        ):
            raise ConversionError(
                "the SEG frames do not lie on the pixel grid of the referenced image "
                "(different orientation, pixel spacing or size); resampled SEGs are not supported"
            )
        i, j, k = _physical_to_index(reference, position[None])[0]
        kk = int(round(k))
        if abs(i) > 0.05 or abs(j) > 0.05 or abs(k - kk) > 0.1 or not 0 <= kk < shape[0]:
            raise ConversionError(
                f"SEG frame {f} at {position.tolist()} does not match a slice of the referenced image "
                f"(index {np.round([i, j, k], 2).tolist()})"
            )
        frame = pixels[f]
        if seg_type == "LABELMAP":
            for number, name in names.items():
                masks[name][kk] |= frame == number
        else:
            number = int(_frame_attr(ds, f, "SegmentIdentificationSequence", "ReferencedSegmentNumber"))
            masks[names[number]][kk] |= frame.astype(bool)
    return masks


def _rtstruct_masks(ds: pydicom.Dataset, reference: sitk.Image) -> dict[str, np.ndarray]:
    from skimage.draw import polygon, polygon_perimeter

    names = {int(r.ROINumber): str(r.ROIName).strip() for r in ds.StructureSetROISequence}
    shape = reference.GetSize()[::-1]
    masks = {}
    for roi in ds.get("ROIContourSequence", []):
        name = names.get(int(roi.ReferencedROINumber))
        if name is None:
            continue
        mask = masks.setdefault(name, np.zeros(shape, dtype=bool))
        for contour in roi.get("ContourSequence", []):
            if contour.get("ContourGeometricType", "CLOSED_PLANAR") != "CLOSED_PLANAR":
                continue
            points = np.array(contour.ContourData, dtype=float).reshape(-1, 3)
            idx = _physical_to_index(reference, points)
            k = idx[:, 2]
            kk = int(round(float(k.mean())))
            if np.ptp(k) > 0.1 or abs(k.mean() - kk) > 0.1 or not 0 <= kk < shape[0]:
                raise ConversionError(f"a contour of ROI '{name}' does not lie on a slice of the referenced image")
            # voxels whose centre lies on the contour belong to it (as with cv2.fillPoly / rt-utils);
            # skimage's polygon alone includes edge voxels inconsistently
            filled = np.zeros(shape[1:], dtype=bool)
            filled[polygon(idx[:, 1], idx[:, 0], shape=shape[1:])] = True
            filled[polygon_perimeter(np.round(idx[:, 1]), np.round(idx[:, 0]), shape=shape[1:])] = True
            # XOR: a contour inside another contour of the same ROI is a hole
            mask[kk] ^= filled
    return masks


def labelmap(
    masks: dict[str, np.ndarray], label_of: dict[str, int], reference: sitk.Image
) -> tuple[sitk.Image, dict[tuple[int, int], int]]:
    """Combine masks into one uint8 label image. Higher label values win where masks overlap.
    Returns the image and {(overwritten label, higher label): number of voxels}."""
    shape = reference.GetSize()[::-1]
    out = np.zeros(shape, dtype=np.uint8)
    overlaps = {}
    for name, mask in sorted(masks.items(), key=lambda kv: label_of[kv[0]]):
        value = label_of[name]
        under, counts = np.unique(out[mask & (out > 0) & (out != value)], return_counts=True)
        for u, n in zip(under.tolist(), counts.tolist()):
            overlaps[(u, value)] = overlaps.get((u, value), 0) + n
        out[mask] = value
    image = sitk.GetImageFromArray(out)
    image.CopyInformation(reference)
    return image, overlaps


# ---------- prediction -> DICOM SEG ----------


def write_seg(
    labels: np.ndarray,
    source_files: list[str],
    label_names: dict[int, str],
    out_file: Path,
    series_description: str,
    algorithm: str,
) -> bool:
    """Label array (z, y, x) on the grid of the source series -> DICOM SEG. False if it is empty."""
    present = sorted(int(v) for v in np.unique(labels) if v)
    segments = [SegSegment(label_names.get(v, f"label {v}"), labels == v) for v in present]
    return write_seg_segments(segments, source_files, out_file, series_description, algorithm)


class SegSegment:
    """One segment of a SEG to write: name, boolean mask (z, y, x) and optionally the coded property
    category and type (pydicom code items) of the segment it came from."""

    def __init__(self, name: str, mask: np.ndarray, category=None, property_type=None):
        self.name, self.mask, self.category, self.property_type = name, mask, category, property_type


def segment_codes(ds: pydicom.Dataset) -> dict[str, tuple]:
    """{segment name: (category item, type item)} of a SEG; RTSTRUCTs carry no such codes."""
    codes = {}
    for s in ds.get("SegmentSequence", []):
        try:
            codes[str(s.SegmentLabel).strip()] = (
                s.SegmentedPropertyCategoryCodeSequence[0],
                s.SegmentedPropertyTypeCodeSequence[0],
            )
        except (AttributeError, IndexError):
            pass
    return codes


def write_seg_segments(
    segments: list[SegSegment],
    source_files: list[str],
    out_file: Path,
    series_description: str,
    algorithm: str,
    algorithm_type: str = "AUTOMATIC",
    series_uid: Optional[str] = None,
    sop_uid: Optional[str] = None,
    series_number: int = 900,
    content_label: Optional[str] = None,
    content_description: Optional[str] = None,
) -> bool:
    """Non-empty boolean masks (z, y, x) on the grid of the source series -> one BINARY DICOM SEG.
    Segments may overlap. Returns False (nothing written) if all masks are empty."""
    import highdicom as hd

    if len(source_files) == 1:
        raise ConversionError("writing SEGs for multi-frame source images is not supported yet")
    segments = [s for s in segments if s.mask.any()]
    if not segments:
        return False
    sources = [pydicom.dcmread(f) for f in source_files]
    tissue = (
        hd.sr.CodedConcept("91723000", "SCT", "Anatomical Structure"),
        hd.sr.CodedConcept("85756007", "SCT", "Tissue"),
    )
    descriptions = []
    for number, segment in enumerate(segments, start=1):
        if segment.category is not None and segment.property_type is not None:
            codes = (
                hd.sr.CodedConcept.from_dataset(segment.category),
                hd.sr.CodedConcept.from_dataset(segment.property_type),
            )
        else:
            codes = tissue
        descriptions.append(
            hd.seg.SegmentDescription(
                segment_number=number,
                segment_label=segment.name[:64],
                segmented_property_category=codes[0],
                segmented_property_type=codes[1],
                algorithm_type=getattr(hd.seg.SegmentAlgorithmTypeValues, algorithm_type),
                algorithm_identification=hd.AlgorithmIdentificationSequence(
                    name=algorithm[:64],
                    version="1",
                    family=hd.sr.CodedConcept("123109", "DCM", "Artificial Intelligence"),
                ),
            )
        )
    seg = hd.seg.Segmentation(
        source_images=sources,
        pixel_array=np.stack([s.mask for s in segments], axis=-1).astype(np.uint8),
        segmentation_type=hd.seg.SegmentationTypeValues.BINARY,
        segment_descriptions=descriptions,
        series_instance_uid=series_uid or hd.UID(),
        series_number=series_number,
        sop_instance_uid=sop_uid or hd.UID(),
        instance_number=1,
        manufacturer="Kaapana",
        manufacturer_model_name="nnU-Net",
        software_versions="nnU-Net",
        device_serial_number="0",
        series_description=series_description[:64],
        content_label=content_label,
        content_description=content_description,
    )
    out_file.parent.mkdir(parents=True, exist_ok=True)
    seg.save_as(out_file)
    return True
