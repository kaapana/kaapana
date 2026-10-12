"""
Wrap an arbitrary binary file (the TRIDENT feature h5) as a DICOM instance,
tagged back to the source WSI series, so it can be sent to PACS.

Generalizes Kaapana's existing Pdf2DcmOperator ("encapsulate + tag with parent
study/series") pattern - but dcmtk's pdf2dcm is PDF-only, so this builds the
instance directly with pydicom instead, using the DICOM "Raw Data Storage" SOP
Class (1.2.840.10008.5.1.4.1.1.66), which exists specifically for private,
vendor-defined binary payloads that don't fit any image/document IOD. Linking
to the source series uses the standard General Reference module
(ReferencedSeriesSequence) - the same mechanism Itk2DcmSegOperator relies on
for DICOM SEG objects.

Payload storage: verified against the actual DICOM standard (PS3.3 sect_C.19,
"Raw Data Module") rather than assumed - the Raw Data Module defines NO public
tag for the binary content at all. It explicitly says to "include any Private
Attributes that contain Raw Data information" and requires a Creator-Version
UID (0008,9123), Type 1, to identify the software/format that produced the
data (so a reader that doesn't recognize that UID knows not to try to
interpret the private bytes itself). An earlier version of this file stored
the payload under (0042,0010) "Document Title" - a short free-text VR ST
element, not a binary payload slot, and non-conformant. Fixed to use a real
private data element under a reserved private creator block instead.
"""
import datetime

import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import generate_uid, ExplicitVRLittleEndian

RAW_DATA_STORAGE_SOP_CLASS_UID = "1.2.840.10008.5.1.4.1.1.66"

# Private block reserved for this encoder's own raw-data payload, per the
# standard DICOM private-attribute reservation mechanism (PS3.5 sect_7.8.1):
# the creator ID string at (gggg,00xx) reserves the (gggg,xx00-xxFF) block for
# elements written by that creator. Using group 0x0071 (odd, private range).
PRIVATE_CREATOR_ID = "KAAPANA TRIDENT 1.0"
PRIVATE_GROUP = 0x0071
PRIVATE_CREATOR_ELEMENT = 0x0010  # reservation slot, block 0x10
PRIVATE_PAYLOAD_ELEMENT = 0x1001  # actual payload, within block 0x10's range

# Fixed (not per-instance) UID identifying this exact raw-data format/encoder
# version, per the Raw Data Module's required Creator-Version UID (0008,9123)
# - a reader seeing this UID knows it's "trident-dicom-utils' own h5-in-DICOM
# encoding, version 1", not an arbitrary unparseable blob.
CREATOR_VERSION_UID = "1.2.826.0.1.3680043.8.498.72256352720638692334357968240508414498"


def build_encapsulated_raw_data_instance(
    payload_bytes: bytes,
    source_level0_dataset: pydicom.Dataset,
    series_description: str,
    content_description: str,
    series_number: int = 400,
    instance_number: int = 1,
) -> Dataset:
    now = datetime.datetime.now()

    ds = Dataset()

    # Patient / Study - copied from the source series so the new instance lands
    # in the same patient/study in PACS.
    for attr in (
        "PatientID",
        "PatientName",
        "PatientBirthDate",
        "PatientSex",
        "StudyInstanceUID",
        "StudyID",
        "StudyDate",
        "StudyTime",
        "AccessionNumber",
        "ReferringPhysicianName",
    ):
        if attr in source_level0_dataset:
            setattr(ds, attr, getattr(source_level0_dataset, attr))

    # Series - new series for this derived object.
    ds.SeriesInstanceUID = generate_uid()
    ds.SeriesNumber = series_number
    ds.SeriesDescription = series_description
    ds.Modality = "OT"  # "Other" - no dedicated modality code for this payload type

    # SOP Common.
    ds.SOPClassUID = RAW_DATA_STORAGE_SOP_CLASS_UID
    ds.SOPInstanceUID = generate_uid()
    ds.InstanceNumber = instance_number
    ds.ContentDate = now.strftime("%Y%m%d")
    ds.ContentTime = now.strftime("%H%M%S")
    # Raw Data Module, Type 1 - see module docstring.
    ds.CreatorVersionUID = CREATOR_VERSION_UID

    # Equipment.
    ds.Manufacturer = "Kaapana"
    ds.ManufacturerModelName = "trident-dicom-utils"
    ds.SoftwareVersions = "0.1.0"

    # General Reference module: link back to the source WSI series/instance.
    ref_instance = Dataset()
    ref_instance.ReferencedSOPClassUID = source_level0_dataset.SOPClassUID
    ref_instance.ReferencedSOPInstanceUID = source_level0_dataset.SOPInstanceUID

    ref_series = Dataset()
    ref_series.SeriesInstanceUID = source_level0_dataset.SeriesInstanceUID
    ref_series.ReferencedInstanceSequence = [ref_instance]
    ds.ReferencedSeriesSequence = [ref_series]

    # The actual payload - a private data element, per the Raw Data Module's
    # own instructions (see module docstring). Reserve the private creator
    # block first, then write the payload into it.
    ds.add_new((PRIVATE_GROUP, PRIVATE_CREATOR_ELEMENT), "LO", PRIVATE_CREATOR_ID)
    ds.add_new((PRIVATE_GROUP, PRIVATE_PAYLOAD_ELEMENT), "OB", payload_bytes)
    ds.ContentDescription = content_description

    ds.file_meta = FileMetaDataset()
    ds.file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
    ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    return ds
