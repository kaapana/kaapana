from datetime import datetime
import struct
import pydicom
from pydicom.uid import (
    generate_uid,
    CTImageStorage,
    RTStructureSetStorage,
    ExplicitVRLittleEndian,
    PYDICOM_IMPLEMENTATION_UID,
    SegmentationStorage,
)
from pydicom.dataset import validate_file_meta
from pydicom.valuerep import PersonName
from pydicom.sequence import Sequence
import pytz


def fill_required_fiels(dcm):
    # Generate consistent UIDs for Dataset
    dcm.StudyInstanceUID = pydicom.uid.UID(generate_uid())
    dcm.SeriesInstanceUID = pydicom.uid.UID(generate_uid())
    dcm.SOPInstanceUID = pydicom.uid.UID(generate_uid())

    dcm.SpecificCharacterSet = "ISO_IR 192"
    # Set required values

    # Prepare complex patient name
    dcm.PatientName = PersonName('SAIC_Pfenning_Prop++luss"2"^1.Messung')
    dcm.PatientID = "123456"
    dcm.StudyDate = "20240205"
    dcm.StudyTime = "120000"
    dcm.Manufacturer = (
        'ÜÖÄßÄ/*-+My üöä+M+SAIC_Pfenning_Propluss"2"^1.Messunga+nurer\{\}@'
    )
    dcm.InstitutionName = "My\{Int\}io+n-12345678900-==][]' @!@##$%^&*()_"
    return dcm


def fill_datetime_related_tags(dcm):
    now = datetime.now()

    # DATETIME

    # Dicom Standard
    dcm.AcquisitionDateTime = now.strftime("%Y%m%d%H%M%S.%f")
    # Adding Trailing Whitespace
    dcm.InstanceCoercionDateTime = now.strftime("%Y%m%d%H%M%S.%f ")
    # Only DateTime Without Seconds
    dcm.RadiopharmaceuticalStartDateTime = now.strftime("%Y%m%d%H%M%S")

    # Shortening
    dcm.DateTimeOfLastCalibration = now.strftime("%Y%m%d%H%M%S.%f")[:18]
    dcm.FrameAcquisitionDateTime = now.strftime("%Y%m%d%H%M%S.%f")[:17]
    dcm.FrameReferenceDateTime = now.strftime("%Y%m%d%H%M%S.%f")[:16]
    dcm.StartAcquisitionDateTime = now.strftime("%Y%m%d%H%M%S")

    # Only Date
    dcm.RadiopharmaceuticalStopDateTime = now.strftime("%Y%m%d%H%M%S")
    dcm.EndAcquisitionDateTime = now.strftime("%Y%m%d%H%M")
    dcm.DecayCorrectionDateTime = now.strftime("%Y%m%d%H")
    dcm.ExclusionStartDateTime = now.strftime("%Y%m%d")
    dcm.InstructionPerformedDateTime = now.strftime("%Y%m")
    dcm.ContributionDateTime = now.strftime("%Y")

    # FIXME make them work!
    # Add Timezone Offset
    minus_timezone = pytz.timezone("America/New_York")
    minus_datetime = now.astimezone(minus_timezone)
    dcm.AttributeModificationDateTime = minus_datetime.strftime(
        "%Y%m%d%H%M%S.%f%z"
    )

    plus_timezone = pytz.timezone("Asia/Kolkata")
    plus_datetime = now.astimezone(plus_timezone)
    dcm.ExpectedCompletionDateTime = plus_datetime.strftime(
        "%Y%m%d%H%M%S.%f%z"
    )

    # Open Cases
    dcm.ScheduledProcedureStepStartDateTime = ""
    dcm.ScheduledProcedureStepModificationDateTime = ""
    dcm.PerformedProcedureStepStartDateTime = ""
    dcm.PerformedProcedureStepEndDateTime = ""
    dcm.ProcedureStepCancellationDateTime = ""

    # DATE
    dcm.StudyDate = now.strftime("%Y%m%d")

    # dcm.ContentDate = now.strftime("%Y%m%d  ")
    # dcm.SeriesDate = now.strftime("%Y%m")
    # dcm.PerformedProcedureStepStartDate = now.strftime("%Y")
    # dcm.PerformedProcedureStepEndDate = now.strftime("%Y.%m.%d")
    # dcm.PresentationCreationDate = now.strftime("%Y-%m-%d")
    # dcm.StructureSetDate = ""

    # TIME
    # dcm.ContentTime = now.strftime("%H%M%S.%f   ")
    # dcm.PresentationCreationTime = now.strftime("%H.%M.%S")
    # dcm.StructureSetTime = now.strftime("%H:%M:%S.%f")

    dcm.StudyTime = now.strftime("%H%M%S.%f")
    dcm.TreatmentControlPointTime = now.strftime("%H%M%S.%f")[:-1]
    dcm.SafePositionExitTime = now.strftime("%H%M%S.%f")[:-2]
    dcm.SafePositionReturnTime = now.strftime("%H%M%S.%f")[:-3]
    dcm.SeriesTime = now.strftime("%H%M%S")
    dcm.PerformedProcedureStepStartTime = now.strftime("%H%M")
    dcm.PerformedProcedureStepEndTime = now.strftime("%H")

    return dcm


def fill_optional_fields(dcm):
    # Additional optional values
    dcm.BodyPartExamined = "HEAD"
    dcm.PatientAge = "030Y"
    dcm.PatientSex = "M"
    dcm.SeriesDescription = "Test+Series"

    # Add custom tags that will be processed by cleanJsonData
    # Custom tag with a '+' in the value
    dcm.PatientComments = "10+15ml contrast agent"
    # Empty tag to test the 'else' condition
    dcm.StudyDescription = ""
    # Tag with a period followed by a space
    dcm.InstitutionalDepartmentName = ".University of J. K. Hopkins+"

    # Set Contrast Agent-related attributes
    dcm.ContrastBolusAgent = "Heparin+Contrast 15+ml"
    dcm.ContrastBolusRoute = "Int@\{rqs\}ave@nou\\s"
    dcm.ContrastBolusStartTime = "120000.000"
    dcm.ContrastBolusStopTime = "121500.000"

    return dcm


def fill_byte_data(dcm):
    # Errors
    dcm.BurnedInAnnotation = "NO"

    float_pixel_data = [1.0, 2.0, 3.0]
    byte_pixel_data_float = struct.pack(
        "f" * len(float_pixel_data), *float_pixel_data
    )
    byte_pixel_data_double = struct.pack(
        "d" * len(float_pixel_data), *float_pixel_data
    )

    # Example of adding a bad pixel image
    dcm.BadPixelImage = b"\x00"

    # Example of adding float pixel data
    dcm.FloatPixelData = byte_pixel_data_float

    # Example of adding double float pixel data
    dcm.DoubleFloatPixelData = byte_pixel_data_double
    # Set pixel data attributes
    dcm.BitsAllocated = 32  # Number of bits allocated for each pixel
    dcm.BitsStored = 32  # Number of bits stored for each pixel
    dcm.PixelRepresentation = 0  # 0 for unsigned, 1 for signed
    dcm.HighBit = 31  # Bit number of the high bit

    # Example of adding float pixel data
    dcm.PixelData = byte_pixel_data_float
    return dcm


def fill_meta(dcm):
    dcm.file_meta.FileMetaInformationGroupLength = 206
    dcm.file_meta.FileMetaInformationVersion = b"\x00\x01"
    dcm.file_meta.ImplementationVersionName = "0.5"
    dcm.file_meta.SourceApplicationEntityTitle = "POSDA;OTHER1"
    dcm.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    dcm.file_meta.MediaStorageSOPInstanceUID = pydicom.uid.UID(generate_uid())
    dcm.file_meta.ImplementationClassUID = PYDICOM_IMPLEMENTATION_UID
    return dcm


def fill_rtstruct(dcm):
    roi_observations_seq = Sequence()
    structure_set_roi_seq = Sequence()

    for idx, label_type in enumerate(["MARKER", "ORGAN", "OTHER", "000000_1"]):
        # Add sub-items to the sequence (example with Observation Number and Referenced ROI Number)
        roi_observation = pydicom.Dataset()
        roi_observation.ObservationNumber = str(idx)
        roi_observation.ReferencedROINumber = str(idx)
        roi_observation.RTROIInterpretedType = label_type
        roi_observations_seq.append(roi_observation)

        # Add items to the sequence (example with ROINumber and ROIName)
        structure_set_roi_item = pydicom.Dataset()
        structure_set_roi_item.ROINumber = str(idx)
        structure_set_roi_item.ROIName = label_type
        structure_set_roi_seq.append(structure_set_roi_item)

    dcm.RTROIObservationsSequence = roi_observations_seq
    dcm.StructureSetROISequence = structure_set_roi_seq

    return dcm


def fill_sequence(dcm):
    sequence_item = pydicom.Dataset()
    sequence_item.CodeValue = "12345"
    sequence_item.CodingSchemeDesignator = "SCT"

    deeper_sequence_item = pydicom.Dataset()
    deeper_sequence_item.CodeMeaning = "Procedure Code"
    sequence_item.ProcedureCodeSequence = [deeper_sequence_item]
    dcm.ProcedureCodeSequence = [sequence_item]

    return dcm


def fill_segmentation(dcm):
    segment_sequence = Sequence()
    for alg_name, alg_type in zip(
        ["TotalSegmentator", "NNuNet"], ["XYZ_123", "A_B_C"]
    ):
        segment = pydicom.Dataset()
        segment.SegmentAlgorithmName = alg_name
        segment.SegmentAlgorithmType = alg_type
        segment.SegmentLabel = "       ;!@#$%^&*()_+=';`;-labelino-    "
        segment_sequence.append(segment)
    dcm.SegmentSequence = segment_sequence
    return dcm


def generate_seg(src_dir, name):
    filename = src_dir / f"{name}.dcm"
    filename.parent.mkdir(exist_ok=True, parents=True)

    dcm = pydicom.Dataset()
    dcm.file_meta = pydicom.dataset.FileMetaDataset()
    dcm = fill_meta(dcm)
    dcm.file_meta.MediaStorageSOPClassUID = SegmentationStorage
    dcm.SOPClassUID = SegmentationStorage
    dcm.Modality = "SEG"

    validate_file_meta(dcm.file_meta, enforce_standard=True)
    dcm = fill_required_fiels(dcm)
    dcm = fill_optional_fields(dcm)
    dcm = fill_byte_data(dcm)
    dcm = fill_segmentation(dcm)
    dcm = fill_datetime_related_tags(dcm)
    dcm = fill_sequence(dcm)
    dcm.save_as(filename, write_like_original=False)


def generate_rtstruct(src_dir, name):
    filename = src_dir / f"{name}.dcm"
    filename.parent.mkdir(exist_ok=True, parents=True)

    dcm = pydicom.Dataset()
    dcm.file_meta = pydicom.dataset.FileMetaDataset()
    dcm = fill_meta(dcm)
    dcm.file_meta.MediaStorageSOPClassUID = RTStructureSetStorage
    dcm.SOPClassUID = RTStructureSetStorage
    dcm.Modality = "RTSTRUCT"

    validate_file_meta(dcm.file_meta, enforce_standard=True)
    dcm = fill_required_fiels(dcm)
    dcm = fill_optional_fields(dcm)
    dcm = fill_byte_data(dcm)
    dcm = fill_rtstruct(dcm)
    dcm = fill_datetime_related_tags(dcm)
    dcm = fill_sequence(dcm)
    dcm.save_as(filename, write_like_original=False)


def generate_ct(src_dir, name):
    filename = src_dir / f"{name}.dcm"
    filename.parent.mkdir(exist_ok=True, parents=True)

    dcm = pydicom.Dataset()
    dcm.file_meta = pydicom.dataset.FileMetaDataset()
    dcm = fill_meta(dcm)
    dcm.file_meta.MediaStorageSOPClassUID = CTImageStorage
    dcm.SOPClassUID = CTImageStorage
    dcm.Modality = "CT"

    validate_file_meta(dcm.file_meta, enforce_standard=True)
    dcm = fill_required_fiels(dcm)
    dcm = fill_optional_fields(dcm)
    dcm = fill_byte_data(dcm)
    dcm = fill_datetime_related_tags(dcm)
    dcm = fill_sequence(dcm)
    dcm.save_as(filename, write_like_original=False)


def generate_dcms(run_dir, batch_name, operator_in_dir):
    generate_ct(
        run_dir / batch_name / "batch1" / operator_in_dir,
        "ct",
    )
    generate_seg(
        run_dir / batch_name / "batch2" / operator_in_dir,
        "seg",
    )
    generate_rtstruct(
        run_dir / batch_name / "batch3" / operator_in_dir,
        "rtstruct",
    )


def generate_test_dicoms(src_dir):
    generate_ct(src_dir, "ct")
    generate_seg(src_dir, "seg")
    generate_rtstruct(src_dir, "rtstruct")
