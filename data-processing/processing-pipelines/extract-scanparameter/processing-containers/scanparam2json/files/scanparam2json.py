# -*- coding: utf-8 -*-

import pydicom
import json
import os
import glob
from datetime import datetime

keywords_basic = [
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "StudyDescription",
    "SeriesDescription",
    "Modality",
    "AcquisitionDateTime",
    "ProcedureCodeSequence",
    "Manufacturer",
    "ManufacturerModelName",
    "DeviceSerialNumber",
    "SoftwareVersions",
    "ProtocolName",
    "BodyPartExamined",
]


# define keywords to extract
keywords_ct = [
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "StudyDescription",
    "SeriesDescription",
    "Modality",
    "AcquisitionDateTime",
    "ProcedureCodeSequence",
    "Manufacturer",
    "ManufacturerModelName",
    "DeviceSerialNumber",
    "SoftwareVersions",
    "ProtocolName",
    "BodyPartExamined",
    "Rows",
    "Columns",
    "PixelSpacing",
    "SliceThickness",
    "PatientPosition",
    "ScanOptions",
    "KVP",
    "DataCollectionDiameter",
    "ReconstructionDiameter",
    "DistanceSourceToDetector",
    "DistanceSourceToPatient",
    "GantryDetectorTilt",
    "TableHeight",
    "RotationDirection",
    "ExposureTime",
    "XRayTubeCurrent",
    "Exposure",
    "FilterType",
    "GeneratorPower",
    "FocalSpots",
    "DateOfLastCalibration",  # "TimeOfLastCalibration",
    "ConvolutionKernel",
    "WaterEquivalentDiameter",
    "WaterEquivalentDiameterCalculationMethodCodeSequence"
    "RevolutionTime"
    "SingleCollimationWidth",
    "TotalCollimationWidth",
    "TableSpeed",
    "TableFeedPerRotation",
    "SpiralPitchFactor",
    "DataCollectionCenterPatient",
    "ReconstructionTargetCenterPatient",
    "ExposureModulationType",
    "EstimatedDoseSaving",
    "CTDIvol",
    "CTDIPhantomTypeCodeSequence",
    "EnergyWeightingFactor",
    "CTAdditionalXRaySourceSequence",
    "MultienergyCTAcquisition"
    # "StudyID", "SeriesNumber", "AcquisitionNumber", "InstanceNumber",
    # "ImagePositionPatient", "ImageOrientationPatient", "FrameOfReferenceUID", "PositionReferenceIndicator",
    # "SliceLocation", "SamplesPerPixel", "PhotometricInterpretation",
    # "BitsAllocated", "BitsStored", "HighBit",
    # "PixelRepresentation", "SmallestImagePixelValue", "LargestImagePixelValue",
    # "WindowCenter", "WindowWidth", "RescaleIntercept", "RescaleSlope", "RescaleType",
    # "WindowCenterWidthExplanation", "RequestedProcedureCodeSequence", "FillerOrderNumberImagingServiceRequest",
]

keywords_mr = [
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "StudyDescription",
    "SeriesDescription",
    "Modality",
    "AcquisitionDateTime",
    "ProcedureCodeSequence",
    "Manufacturer",
    "ManufacturerModelName",
    "DeviceSerialNumber",
    "SoftwareVersions",
    "ProtocolName",
    "BodyPartExamined",
    "Rows",
    "Columns",
    "PixelSpacing",
    "SliceThickness",
    "PatientPosition",
    "ScanningSequence",
    "SequenceVariant",
    "ScanOptions",
    "MRAcquisitionType",
    "SequenceName",
    "AngioFlag",
    "RepetitionTime",
    "EchoTime",
    "InversionTime",
    "NumberOfAverages",
    "ImagingFrequency",
    "ImagedNucleus",
    "EchoNumbers",
    "MagneticFieldStrength",
    "NumberOfPhaseEncodingSteps",
    "EchoTrainLength",
    "PercentSampling",
    "PercentPhaseFieldOfView",
    "PixelBandwidth",
    "TriggerTime",
    "ReconstructionDiameter",
    "ReceiveCoilName",
    "TransmitCoilName",
    "AcquisitionMatrix",
    "InPlanePhaseEncodingDirection",
    "FlipAngle",
    "VariableFlipAngleFlag",
    "SAR",
    "dBdt",
    "B1rms"
    # "StudyID", "SeriesNumber", "AcquisitionNumber", "InstanceNumber",
    # "ImagePositionPatient", "ImageOrientationPatient", "FrameOfReferenceUID", "PositionReferenceIndicator",
    # "SliceLocation", "SamplesPerPixel", "PhotometricInterpretation",
    # "BitsAllocated", "BitsStored", "HighBit",
    # "PixelRepresentation", "SmallestImagePixelValue", "LargestImagePixelValue",
    # "WindowCenter", "WindowWidth", "RescaleIntercept", "RescaleSlope", "RescaleType",
    # "WindowCenterWidthExplanation", "RequestedProcedureCodeSequence", "FillerOrderNumberImagingServiceRequest",
]


# From the template
batch_folders = [
    f
    for f in glob.glob(
        os.path.join("/", os.environ["WORKFLOW_DIR"], os.environ["BATCH_NAME"], "*")
    )
]

json_list = []

for batch_element_dir in batch_folders:
    element_input_dir = os.path.join(batch_element_dir, os.environ["OPERATOR_IN_DIR"])
    element_output_dir = os.path.join(batch_element_dir, os.environ["OPERATOR_OUT_DIR"])
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)

    # The processing algorithm
    print(
        f"Checking {element_input_dir} for dcm files and writing results to {element_output_dir}"
    )
    dcm_files = sorted(
        glob.glob(os.path.join(element_input_dir, "*.dcm*"), recursive=True)
    )

    if len(dcm_files) == 0:
        print("No dicom file found!")
        exit(1)
    else:
        scan_mappings = []
        print(f"Extracting study_id from: {dcm_files[0]}")
        dcm = pydicom.dcmread(dcm_files[0], force=True)

        json_dict = {}

        # check modality of the scan
        modality = str(dcm["Modality"].value)
        if modality == "CT":
            keywords = keywords_ct
        elif modality == "MR":
            keywords = keywords_mr
        else:
            print(f"unknown modality: {modality}")
            keywords = keywords_basic

        for key in keywords:
            try:
                if (
                    dcm[key].repval == "<Sequence, length 1>"
                ):  # need to deal with sequence
                    print(f"{key} is a sequence")
                    # print(dcm[key].value)
                    ds = dcm[key].value[0]
                    i = 0
                    seq_list = []
                    while i < len(ds):
                        seq_key = dir(ds)[i]
                        seq_value = str(ds[seq_key].value)
                        seq_list.append(seq_value)
                        i += 1
                    json_dict[key] = seq_list
                else:
                    json_dict[key] = str(dcm[key].value)
            except:
                json_dict[key] = ""

        print(json_dict)
        json_list.append(json_dict)


batch_output_dir = os.path.join(
    "/", os.environ["WORKFLOW_DIR"], os.environ["OPERATOR_OUT_DIR"]
)
if not os.path.exists(batch_output_dir):
    os.makedirs(batch_output_dir)

json_file_path = os.path.join(
    batch_output_dir,
    "scan_parameters_{}.json".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
)

print(json_file_path)

with open(json_file_path, "w", encoding="utf-8") as jsonData:
    json.dump(json_list, jsonData, indent=4, sort_keys=False, ensure_ascii=True)
