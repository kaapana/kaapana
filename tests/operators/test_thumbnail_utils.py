import sys
from pathlib import Path

import pydicom
import pytest

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "data-processing/kaapana-plugin/extension/docker/files/plugin"
    ),
)

from kaapana.operators.HelperThumbnails import NO_THUMBNAIL_MODALITIES, has_ref_series


@pytest.mark.parametrize(
    "modality,expected",
    [
        ("SEG", True),
        ("RTSTRUCT", True),
        ("CT", False),
        ("MR", False),
        ("SR", False),
        ("KO", False),
        ("PR", False),
        ("RTPLAN", False),
        ("REG", False),
        ("PT", False),
    ],
)
def test_has_ref_series_by_modality(modality, expected):
    ds = pydicom.Dataset()
    ds.Modality = modality
    assert has_ref_series(ds) == expected


def test_has_ref_series_seg_by_sop_class_uid():
    ds = pydicom.Dataset()
    ds.Modality = "UNKNOWN"
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.66.4"  # Segmentation Storage
    assert has_ref_series(ds) is True


def test_has_ref_series_rtstruct_by_sop_class_uid():
    ds = pydicom.Dataset()
    ds.Modality = "UNKNOWN"
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.481.3"  # RT Structure Set Storage
    assert has_ref_series(ds) is True


@pytest.mark.parametrize("modality", sorted(NO_THUMBNAIL_MODALITIES))
def test_no_thumbnail_modality_never_has_ref_series(modality):
    ds = pydicom.Dataset()
    ds.Modality = modality
    assert has_ref_series(ds) is False


@pytest.mark.parametrize(
    "modality,should_skip",
    [
        ("SR", True),
        ("KO", True),
        ("PR", True),
        ("RTPLAN", True),
        ("REG", True),
        ("FID", True),
        ("AU", True),
        ("RWVM", True),
        ("CT", False),
        ("MR", False),
        ("SEG", False),
        ("RTSTRUCT", False),
        ("PT", False),
    ],
)
def test_no_thumbnail_modalities_set(modality, should_skip):
    assert (modality in NO_THUMBNAIL_MODALITIES) == should_skip
