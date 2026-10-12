"""
Shared helpers for reading a local directory of DICOM VL Whole Slide Microscopy
Image instances (one Kaapana batch-element's worth of .dcm files, as downloaded
by GetInputOperator) and identifying the level-0 (highest-resolution) instance.
"""
import glob
import os
from dataclasses import dataclass
from typing import List, Optional

import pydicom


@dataclass
class DicomLevel:
    path: str
    dataset: pydicom.Dataset  # read with stop_before_pixels=True - headers only
    total_pixel_matrix_columns: int
    total_pixel_matrix_rows: int
    mpp: float  # microns per pixel (row spacing)


def _mpp_from_dataset(ds: pydicom.Dataset) -> Optional[float]:
    """
    WSI DICOM instances carry pixel spacing in the per-frame functional groups,
    usually shared across all frames via SharedFunctionalGroupsSequence.
    Falls back to a plain top-level PixelSpacing if present (defensive only).
    """
    try:
        shared = ds.SharedFunctionalGroupsSequence[0]
        pixel_measures = shared.PixelMeasuresSequence[0]
        row_spacing_mm = float(pixel_measures.PixelSpacing[0])
        return round(row_spacing_mm * 1000, 6)
    except (AttributeError, IndexError, KeyError):
        pass

    if "PixelSpacing" in ds:
        return round(float(ds.PixelSpacing[0]) * 1000, 6)

    return None


def list_pyramid_levels(dicom_dir: str) -> List[DicomLevel]:
    """
    Reads headers of every .dcm file in `dicom_dir` and returns the ones that are
    genuine pyramid levels (i.e. carry TotalPixelMatrixColumns/Rows - excludes
    LABEL/OVERVIEW/THUMBNAIL auxiliary images that a WSI DICOM instance set may
    also contain), sorted descending by resolution (index 0 = highest-res / level-0).
    """
    levels: List[DicomLevel] = []
    for path in sorted(glob.glob(os.path.join(dicom_dir, "*.dcm"))):
        ds = pydicom.dcmread(path, stop_before_pixels=True)

        cols = getattr(ds, "TotalPixelMatrixColumns", None)
        rows = getattr(ds, "TotalPixelMatrixRows", None)
        if cols is None or rows is None:
            continue  # not a pyramid level (e.g. LABEL/OVERVIEW image)

        image_type = list(getattr(ds, "ImageType", []))
        if any(flag in image_type for flag in ("LABEL", "OVERVIEW", "THUMBNAIL")):
            continue

        mpp = _mpp_from_dataset(ds)
        if mpp is None:
            continue

        levels.append(
            DicomLevel(
                path=path,
                dataset=ds,
                total_pixel_matrix_columns=int(cols),
                total_pixel_matrix_rows=int(rows),
                mpp=mpp,
            )
        )

    if not levels:
        raise FileNotFoundError(f"No DICOM WSI pyramid levels found under {dicom_dir}")

    levels.sort(key=lambda lvl: lvl.total_pixel_matrix_columns, reverse=True)
    return levels


def read_source_uids(level0: DicomLevel) -> dict:
    ds = level0.dataset
    return {
        "study_instance_uid": str(ds.StudyInstanceUID),
        "series_instance_uid": str(ds.SeriesInstanceUID),
        "sop_instance_uid": str(ds.SOPInstanceUID),
        "sop_class_uid": str(ds.SOPClassUID),
        "patient_id": getattr(ds, "PatientID", ""),
        "patient_name": str(getattr(ds, "PatientName", "")),
    }
