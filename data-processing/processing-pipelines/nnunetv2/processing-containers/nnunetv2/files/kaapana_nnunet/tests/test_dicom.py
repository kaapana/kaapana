"""DICOM conversion tests on synthetic series: SEG frames and RTSTRUCT contours must land on the exact voxels."""

import numpy as np
import pydicom
import pytest
import SimpleITK as sitk
from kaapana_nnunet import dicom
from pydicom.dataset import FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

hd = pytest.importorskip("highdicom")

SHAPE = (6, 20, 24)  # z, y, x
SPACING = (0.8, 0.7, 2.5)  # x, y, z
ORIGIN = (-10.0, 20.0, 30.0)


def make_ct(tmp_path, orientation=(1, 0, 0, 0, 1, 0), shuffle=True):
    study, series, frame = generate_uid(), generate_uid(), generate_uid()
    row, col = np.array(orientation[:3], float), np.array(orientation[3:], float)
    normal = np.cross(row, col)
    rng = np.random.default_rng(1)
    volume = rng.integers(-1000, 1000, size=SHAPE).astype(np.int16)
    out = tmp_path / "ct"
    out.mkdir()
    datasets = []
    order = list(range(SHAPE[0]))
    if shuffle:
        rng.shuffle(order)
    for z in order:
        ds = pydicom.Dataset()
        ds.file_meta = FileMetaDataset()
        ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        ds.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
        ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
        ds.SOPInstanceUID = generate_uid()
        ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
        ds.PatientName, ds.PatientID, ds.PatientBirthDate, ds.PatientSex = "Test", "T1", "", "O"
        ds.StudyInstanceUID, ds.SeriesInstanceUID, ds.FrameOfReferenceUID = study, series, frame
        ds.StudyID, ds.StudyDate, ds.StudyTime, ds.AccessionNumber, ds.ReferringPhysicianName = "1", "", "", "", ""
        ds.Modality, ds.SeriesNumber, ds.InstanceNumber = "CT", 1, z + 1
        ds.Manufacturer = "test"
        ds.ImageOrientationPatient = list(orientation)
        pos = np.array(ORIGIN) + z * SPACING[2] * normal
        ds.ImagePositionPatient = pos.tolist()
        ds.PixelSpacing = [SPACING[1], SPACING[0]]
        ds.SliceThickness = SPACING[2]
        ds.Rows, ds.Columns = SHAPE[1], SHAPE[2]
        ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, "MONOCHROME2"
        ds.BitsAllocated, ds.BitsStored, ds.HighBit, ds.PixelRepresentation = 16, 16, 15, 1
        ds.RescaleIntercept, ds.RescaleSlope = 0, 1
        ds.PixelData = volume[z].tobytes()
        ds.save_as(out / f"{ds.SOPInstanceUID}.dcm", enforce_file_format=True)
        datasets.append(ds)
    datasets.sort(key=lambda d: d.InstanceNumber)
    return out, datasets, volume


def make_seg(datasets, masks, seg_type=hd.seg.SegmentationTypeValues.BINARY):
    descriptions = [
        hd.seg.SegmentDescription(
            segment_number=i + 1,
            segment_label=name,
            segmented_property_category=hd.sr.CodedConcept("91723000", "SCT", "Anatomical Structure"),
            segmented_property_type=hd.sr.CodedConcept("10200004", "SCT", "Liver"),
            algorithm_type=hd.seg.SegmentAlgorithmTypeValues.MANUAL,
        )
        for i, name in enumerate(masks)
    ]
    stacked = np.stack(list(masks.values()), axis=-1).astype(np.uint8)
    return hd.seg.Segmentation(
        source_images=datasets,
        pixel_array=stacked,
        segmentation_type=seg_type,
        segment_descriptions=descriptions,
        series_instance_uid=generate_uid(),
        series_number=2,
        sop_instance_uid=generate_uid(),
        instance_number=1,
        manufacturer="test",
        manufacturer_model_name="test",
        software_versions="1",
        device_serial_number="1",
        **({"max_fractional_value": 1} if seg_type == hd.seg.SegmentationTypeValues.FRACTIONAL else {}),
    )


def two_masks():
    a = np.zeros(SHAPE, bool)
    a[1:4, 2:9, 3:12] = True
    b = np.zeros(SHAPE, bool)
    b[3:5, 10:15, 5:20] = True  # overlaps a on slice 3? no: rows 10-14 vs 2-8 -> disjoint in-plane
    b[2, 0, 0] = True  # single voxel in the corner
    return {"Liver": a, "Tumor": b}


def test_read_image_series_orders_slices(tmp_path):
    folder, _, volume = make_ct(tmp_path)
    image = dicom.read_image_series(folder)
    assert image.GetSize() == SHAPE[::-1]
    np.testing.assert_allclose(image.GetSpacing(), SPACING, atol=1e-4)
    np.testing.assert_array_equal(sitk.GetArrayFromImage(image), volume)


@pytest.mark.parametrize("seg_type", ["BINARY", "FRACTIONAL"])
@pytest.mark.parametrize("orientation", [(1, 0, 0, 0, 1, 0), (0, 1, 0, 0, 0, -1)])
def test_seg_lands_on_the_right_voxels(tmp_path, seg_type, orientation):
    folder, datasets, _ = make_ct(tmp_path, orientation=orientation)
    image = dicom.read_image_series(folder)
    masks = two_masks()
    seg = make_seg(datasets, masks, getattr(hd.seg.SegmentationTypeValues, seg_type))
    seg.save_as(tmp_path / "seg.dcm")
    ds = pydicom.dcmread(tmp_path / "seg.dcm")

    assert dicom.referenced_series_uid(ds) == datasets[0].SeriesInstanceUID
    got = dicom.segment_masks(ds, image)
    assert set(got) == {"Liver", "Tumor"}
    for name, mask in masks.items():
        np.testing.assert_array_equal(got[name], mask, err_msg=name)


def test_labelmap_overlap_higher_label_wins(tmp_path):
    folder, _, _ = make_ct(tmp_path)
    image = dicom.read_image_series(folder)
    a = np.zeros(SHAPE, bool)
    a[1:3, 1:5, 1:5] = True
    b = np.zeros(SHAPE, bool)
    b[2, 1:3, 1:3] = True
    label, overlaps = dicom.labelmap({"a": a, "b": b}, {"a": 1, "b": 2}, image)
    arr = sitk.GetArrayFromImage(label)
    assert arr[2, 1, 1] == 2 and arr[1, 1, 1] == 1 and arr[0, 0, 0] == 0
    assert overlaps == {(1, 2): 4}
    assert dicom.same_geometry(label, image)


def test_seg_on_other_grid_is_rejected(tmp_path):
    folder, datasets, _ = make_ct(tmp_path)
    seg = make_seg(datasets, two_masks())
    seg.save_as(tmp_path / "seg.dcm")
    ds = pydicom.dcmread(tmp_path / "seg.dcm")
    other = sitk.Image(SHAPE[2] * 2, SHAPE[1] * 2, SHAPE[0], sitk.sitkInt16)
    other.SetSpacing((SPACING[0] / 2, SPACING[1] / 2, SPACING[2]))
    other.SetOrigin(ORIGIN)
    with pytest.raises(dicom.ConversionError):
        dicom.segment_masks(ds, other)


def make_rtstruct(datasets, contours):
    """contours: {roi name: [(z index, [(x index, y index), ...]), ...]} in voxel coordinates."""
    ref = datasets[0]
    ds = pydicom.Dataset()
    ds.Modality = "RTSTRUCT"
    ds.StructureSetROISequence = Sequence()
    ds.ROIContourSequence = Sequence()
    frame = pydicom.Dataset()
    study = pydicom.Dataset()
    series = pydicom.Dataset()
    series.SeriesInstanceUID = ref.SeriesInstanceUID
    study.RTReferencedSeriesSequence = Sequence([series])
    frame.RTReferencedStudySequence = Sequence([study])
    ds.ReferencedFrameOfReferenceSequence = Sequence([frame])
    for number, (name, items) in enumerate(contours.items(), start=1):
        roi = pydicom.Dataset()
        roi.ROINumber, roi.ROIName = number, name
        ds.StructureSetROISequence.append(roi)
        rc = pydicom.Dataset()
        rc.ReferencedROINumber = number
        rc.ContourSequence = Sequence()
        for z, pts in items:
            c = pydicom.Dataset()
            c.ContourGeometricType = "CLOSED_PLANAR"
            world = [np.array(ORIGIN) + np.array([x * SPACING[0], y * SPACING[1], z * SPACING[2]]) for x, y in pts]
            c.ContourData = np.concatenate(world).tolist()
            c.NumberOfContourPoints = len(pts)
            rc.ContourSequence.append(c)
        ds.ROIContourSequence.append(rc)
    return ds


def test_rtstruct_with_hole(tmp_path):
    folder, datasets, _ = make_ct(tmp_path, shuffle=False)
    image = dicom.read_image_series(folder)
    outer = [(2, 2), (12, 2), (12, 12), (2, 12)]
    inner = [(5, 5), (8, 5), (8, 8), (5, 8)]
    ds = make_rtstruct(datasets, {"Body": [(2, outer), (2, inner)], "Spot": [(4, [(1, 1), (3, 1), (3, 3), (1, 3)])]})
    assert dicom.referenced_series_uid(ds) == datasets[0].SeriesInstanceUID
    got = dicom.segment_masks(ds, image)
    body = got["Body"]
    assert body[2, 3, 3] and body[2, 11, 11]
    assert not body[2, 6, 6]  # the hole
    assert not body[1].any() and not body[3].any()
    assert got["Spot"][4, 2, 2] and got["Spot"][4].sum() == 9


def test_write_seg_segments_round_trip_keeps_codes_and_uids(tmp_path):
    folder, datasets, _ = make_ct(tmp_path)
    image, files = dicom.read_image_series(folder, with_files=True)
    masks = two_masks()
    masks["Tumor"] = masks["Tumor"] | masks["Liver"]  # segments of one SEG may overlap
    source = make_seg(datasets, {"Liver": masks["Liver"]})
    category, kind = dicom.segment_codes(source)["Liver"]
    segments = [dicom.SegSegment("Liver", masks["Liver"], category, kind), dicom.SegSegment("Tumor", masks["Tumor"])]
    uids = dict(series_uid="1.2.3.4", sop_uid="1.2.3.5")
    first, second = tmp_path / "a" / "seg.dcm", tmp_path / "b" / "seg.dcm"
    for out in (first, second):
        assert dicom.write_seg_segments(
            segments, files, out, "Harmonized", "Kaapana harmonize", "SEMIAUTOMATIC", **uids, content_label="HARMONIZED"
        )
    ds = pydicom.dcmread(first)
    assert ds.SeriesInstanceUID == "1.2.3.4" and ds.SOPInstanceUID == "1.2.3.5" and ds.ContentLabel == "HARMONIZED"
    assert ds.SegmentSequence[0].SegmentedPropertyTypeCodeSequence[0].CodeMeaning == "Liver"
    assert ds.SegmentSequence[1].SegmentedPropertyTypeCodeSequence[0].CodeMeaning == "Tissue"
    got = dicom.segment_masks(ds, image)
    for name in ("Liver", "Tumor"):
        np.testing.assert_array_equal(got[name], masks[name], err_msg=name)
    empty = [dicom.SegSegment("x", np.zeros(SHAPE, bool))]
    assert not dicom.write_seg_segments(empty, files, tmp_path / "c.dcm", "", "")
