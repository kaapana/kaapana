from datetime import datetime
from pydicom.uid import (
    UID,
    generate_uid,
    CTImageStorage,
    RTStructureSetStorage,
    ExplicitVRLittleEndian,
    PYDICOM_IMPLEMENTATION_UID,
    SegmentationStorage,
)
from pydicom import Dataset
from pydicom.dataset import validate_file_meta, FileMetaDataset
from pydicom.valuerep import PersonName
from pydicom.sequence import Sequence

import struct
import pytz
import copy


def fill_rtstruct(dcm):
    roi_observations_seq = Sequence()
    structure_set_roi_seq = Sequence()

    for idx, label_type in enumerate(["MARKER", "ORGAN", "OTHER", "000000_1"]):
        # Add sub-items to the sequence (example with Observation Number and Referenced ROI Number)
        roi_observation = Dataset()
        roi_observation.ObservationNumber = str(idx)
        roi_observation.ReferencedROINumber = str(idx)
        roi_observation.RTROIInterpretedType = label_type
        roi_observations_seq.append(roi_observation)

        # Add items to the sequence (example with ROINumber and ROIName)
        structure_set_roi_item = Dataset()
        structure_set_roi_item.ROINumber = str(idx)
        structure_set_roi_item.ROIName = label_type
        structure_set_roi_seq.append(structure_set_roi_item)

    dcm.RTROIObservationsSequence = roi_observations_seq
    dcm.StructureSetROISequence = structure_set_roi_seq

    return dcm


def fill_sequence(dcm):
    sequence_item = Dataset()
    sequence_item.CodeValue = "12345"
    sequence_item.CodingSchemeDesignator = "SCT"

    deeper_sequence_item = Dataset()
    deeper_sequence_item.CodeMeaning = "Procedure Code"
    sequence_item.ProcedureCodeSequence = [deeper_sequence_item]
    dcm.ProcedureCodeSequence = [sequence_item]

    return dcm


def fill_segmentation(dcm):
    segment_sequence = Sequence()
    for alg_name, alg_type, alg_label in zip(
        ["TotalSegmentator", "NNuNet", None, []],
        ["XYZ_123", "A_B_C", None, []],
        ["       ;!@#$%^&*()_+=';`;-labelino-    ", "label", None, []],
    ):
        segment = Dataset()
        if alg_name:
            segment.SegmentAlgorithmName = alg_name
        if alg_type:
            segment.SegmentAlgorithmType = alg_type
        if alg_label:
            segment.SegmentLabel = alg_label
        segment_sequence.append(segment)
    dcm.SegmentSequence = segment_sequence
    return dcm


def generate_dcm(params):
    default_params = copy.deepcopy(DEFAULT_PARAMS)
    default_params.update(params)
    dcm = Dataset()
    dcm.file_meta = FileMetaDataset()

    for tag_name, value in default_params.items():
        if tag_name.startswith("file_meta"):
            tag_name = tag_name.split(".")[-1]
            setattr(dcm.file_meta, tag_name, value)
        else:
            setattr(dcm, tag_name, value)

    return dcm


def generate_ct(filename, params):
    params["file_meta.MediaStorageSOPClassUID"] = CTImageStorage
    params["SOPClassUID"] = CTImageStorage
    params["Modality"] = "CT"

    dcm = generate_dcm(params)
    dcm = fill_sequence(dcm)

    validate_file_meta(dcm.file_meta, enforce_standard=True)
    filename.parent.mkdir(exist_ok=True, parents=True)
    dcm.save_as(filename, write_like_original=False)


def generate_rtstruct(filename, params):
    params["file_meta.MediaStorageSOPClassUID"] = RTStructureSetStorage
    params["SOPClassUID"] = RTStructureSetStorage
    params["Modality"] = "RTSTRUCT"

    dcm = generate_dcm(params)
    dcm = fill_rtstruct(dcm)
    dcm = fill_sequence(dcm)

    validate_file_meta(dcm.file_meta, enforce_standard=True)
    filename.parent.mkdir(exist_ok=True, parents=True)
    dcm.save_as(filename, write_like_original=False)


def generate_seg(filename, params):
    params["file_meta.MediaStorageSOPClassUID"] = SegmentationStorage
    params["SOPClassUID"] = SegmentationStorage
    params["Modality"] = "SEG"

    dcm = generate_dcm(params)
    dcm = fill_segmentation(dcm)
    dcm = fill_sequence(dcm)

    validate_file_meta(dcm.file_meta, enforce_standard=True)
    filename.parent.mkdir(exist_ok=True, parents=True)
    dcm.save_as(filename, write_like_original=False)


NOW = datetime.now()
minus_timezone = pytz.timezone("America/New_York")
MINUS_DATETIME = NOW.astimezone(minus_timezone)

plus_timezone = pytz.timezone("Asia/Kolkata")
PLUS_DATETIME = NOW.astimezone(plus_timezone)

float_pixel_data = [1.0, 2.0, 3.0]
byte_pixel_data_float = struct.pack("f" * len(float_pixel_data), *float_pixel_data)
byte_pixel_data_double = struct.pack("d" * len(float_pixel_data), *float_pixel_data)

DEFAULT_PARAMS = {
    #
    # FileMetadata
    #
    "file_meta.FileMetaInformationGroupLength": 206,
    "file_meta.FileMetaInformationVersion": b"\x00\x01",
    "file_meta.ImplementationVersionName": "0.5",
    "file_meta.SourceApplicationEntityTitle": "POSDA;OTHER1",
    "file_meta.TransferSyntaxUID": ExplicitVRLittleEndian,
    "file_meta.MediaStorageSOPInstanceUID": UID(generate_uid()),
    "file_meta.ImplementationClassUID": PYDICOM_IMPLEMENTATION_UID,
    #
    # RequiredFields
    #
    "StudyInstanceUID": UID(generate_uid()),
    "SeriesInstanceUID": UID(generate_uid()),
    "SOPInstanceUID": UID(generate_uid()),
    "SpecificCharacterSet": "ISO_IR 192",
    "PatientName": PersonName('SAIC_Pfenning_Prop++luss"2"^1.Messung'),
    "PatientID": "123456",
    "StudyDate": "20240205",
    "StudyTime": "120000",
    "Manufacturer": 'ÜÖÄßÄ/*-+My üöä+M+SAIC_Pfenning_Propluss"2"^1.Messunga+nurer\\{\\}@',
    "InstitutionName": "My\\{Int\\}io+n-12345678900-==][]' @!@##$%^&*()_",
    #
    # Datetime
    #
    # Standard
    "AcquisitionDateTime": NOW.strftime("%Y%m%d%H%M%S.%f"),
    # Adding Trailing Whitespace
    "InstanceCoercionDateTime": NOW.strftime("%Y%m%d%H%M%S.%f "),
    # Only DateTime Without Seconds
    "RadiopharmaceuticalStartDateTime": NOW.strftime("%Y%m%d%H%M%S"),
    # Shortening
    "DateTimeOfLastCalibration": NOW.strftime("%Y%m%d%H%M%S.%f")[:18],
    "FrameAcquisitionDateTime": NOW.strftime("%Y%m%d%H%M%S.%f")[:17],
    "FrameReferenceDateTime": NOW.strftime("%Y%m%d%H%M%S.%f")[:16],
    "StartAcquisitionDateTime": NOW.strftime("%Y%m%d%H%M%S"),
    # Only Date
    "RadiopharmaceuticalStopDateTime": NOW.strftime("%Y%m%d%H%M%S"),
    "EndAcquisitionDateTime": NOW.strftime("%Y%m%d%H%M"),
    "ExclusionStartDateTime": NOW.strftime("%Y%m%d"),
    "InstructionPerformedDateTime": NOW.strftime("%Y%m"),
    "ContributionDateTime": NOW.strftime("%Y"),
    # FIXME make them work!
    # Add Timezone Offset
    # "AttributeModificationDateTime": minus_datetime.strftime("%Y%m%d%H%M%S.%f%z"),
    # "ExpectedCompletionDateTime": plus_datetime.strftime("%Y%m%d%H%M%S.%f%z"),
    # Open Cases
    "ScheduledProcedureStepStartDateTime": "",
    "ScheduledProcedureStepModificationDateTime": "",
    "PerformedProcedureStepStartDateTime": "",
    "PerformedProcedureStepEndDateTime": "",
    "ProcedureStepCancellationDateTime": "",
    # DATE
    "ContentDate": NOW.strftime("%Y%m%d"),
    "SeriesDate": "",
    "PerformedProcedureStepStartDate": "",
    "PerformedProcedureStepEndDate": "",
    "PresentationCreationDate": "",
    "StructureSetDate": "",
    # TIME
    "ContentTime": NOW.strftime("%H%M%S.%f"),
    "TreatmentControlPointTime": NOW.strftime("%H%M%S.%f")[:-1],
    "SafePositionExitTime": NOW.strftime("%H%M%S.%f")[:-2],
    "SafePositionReturnTime": NOW.strftime("%H%M%S.%f")[:-3],
    "SeriesTime": NOW.strftime("%H%M%S"),
    "PerformedProcedureStepStartTime": NOW.strftime("%H%M"),
    "PerformedProcedureStepEndTime": NOW.strftime("%H"),
    "PresentationCreationTime": "",
    "StructureSetTime": "",
    #
    # Additional optional values
    #
    "BodyPartExamined": "HEAD",
    "PatientSex": "M",
    "SeriesDescription": "Test+Series",
    # Add custom tags that will be processed by LocalDcm2Json._clean_json(self, metadata):
    # Custom tag with a '+' in the value
    "PatientComments": "10+15ml contrast agent",
    # Empty tag to test the 'else' condition
    "StudyDescription": "",
    # Tag with a period followed by a space
    "InstitutionalDepartmentName": ".University of J. K. Hopkins+",
    # Set Contrast Agent-related attributes
    "ContrastBolusAgent": "Heparin+Contrast 15+ml",
    "ContrastBolusRoute": "Int@\\{rqs\\}ave@nou\\s",
    "ContrastBolusStartTime": "120000.000",
    "ContrastBolusStopTime": "121500.000",
    #
    # Byte Data
    #
    # Errors
    "BurnedInAnnotation": "NO",
    # Example of adding a bad pixel image
    "BadPixelImage": b"\x00",
    # Example of adding float pixel data
    "FloatPixelData": byte_pixel_data_float,
    # Example of adding double float pixel data
    "DoubleFloatPixelData": byte_pixel_data_double,
    # Set pixel data attributes
    "BitsAllocated": 32,  # Number of bits allocated for each pixel
    "BitsStored": 32,  # Number of bits stored for each pixel
    "PixelRepresentation": 0,  # 0 for unsigned, 1 for signed
    "HighBit": 31,  # Bit number of the high bit
    # Example of adding float pixel data
    "PixelData": byte_pixel_data_float,
    #
    # PatientAge
    #
    "PatientAge": "032Y",
    "PatientBirthDate": "19900101",
}
