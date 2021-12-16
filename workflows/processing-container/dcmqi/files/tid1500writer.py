
import os
from os import getenv
from os.path import join, exists, dirname, basename, realpath
from glob import glob
from pathlib import Path
import json
import pydicom
from pydicom.uid import generate_uid

# For shell-execution
from subprocess import PIPE, run
execution_timeout = 10

# Counter to check if smth has been processed
processed_count = 0

# Alternative Process smth via shell-command

code_lookup_table_path = join(dirname(realpath(__file__)), "code_lookup_table.json")
with open(code_lookup_table_path) as f:
    code_lookup_table = json.load(f)

def find_code_meaning(tag):
    result = None
    print("#####################################################")
    print("#")
    print(f"Searching for identical hit for {tag}...")
    tag = tag.lower()
    for entry in code_lookup_table:
        if tag.replace(" ", "-") == entry["Code Meaning"].lower().replace(" ", "-"):
            print(f"Found Code Meaning: {entry['Code Meaning'].lower()} for search term: {tag}")
            result = entry
            break
        elif tag == entry["Body Part Examined"].lower():
            print(f"Found Code Meaning: {entry['Body Part Examined'].lower()} for search term: {tag}")
            result = entry
            break

    if result == None:
        print(f"Nothing found -> Searching if {tag} is in one of the entires...")
        for entry in code_lookup_table:
            if tag in entry["Code Meaning"].lower():
                print(f"Found Code Meaning: {entry['Code Meaning'].lower()} for search term: {tag}")
                result = entry
                break
            elif tag in entry["Body Part Examined"].lower():
                print(f"Found Code Meaning: {entry['Body Part Examined'].lower()} for search term: {tag}")
                result = entry
                break

    if result == None:
        print(f"Nothing found -> Searching if {tag} parts equals one of the entires...")
        for entry in code_lookup_table:
            for tag_part in tag.split(" "):
                if tag_part == entry["Code Meaning"].lower():
                    print(f"Found Code Meaning: {entry['Code Meaning'].lower()} for search term: {tag_part.lower()}")
                    result = entry
                    break
                elif tag_part == entry["Body Part Examined"].lower():
                    print(f"Found Code Meaning: {entry['Body Part Examined'].lower()} for search term: {tag_part.lower()}")
                    result = entry
                    break
            if result != None:
                break

    if result == None:
        print(f"Nothing found -> Searching if {tag} parts can be found in one of the entires...")
        for entry in code_lookup_table:
            for tag_part in tag.split(" "):
                if tag_part in entry["Code Meaning"].lower():
                    print(f"Found Code Meaning: {entry['Code Meaning'].lower()} for search term: {tag_part.lower()}")
                    result = entry
                    break
                elif tag_part in entry["Body Part Examined"].lower():
                    print(f"Found Code Meaning: {entry['Body Part Examined'].lower()} for search term: {tag_part.lower()}")
                    result = entry
                    break
            if result != None:
                break

    if result == None:
        raise AssertionError(f"Could not find the tag: '{tag}' in the lookup table!")

    print("#")
    print("#####################################################")
    return result


def create_measurements_json(json_path, src_dicom_dir, seg_dicom_dir):
    global series_description

    new_series_number = 1
    compositeContext = []
    if seg_dicom_dir is not None:
        seg_dicom_files_found = glob(join(seg_dicom_dir, "*.dcm"), recursive=False)
        print(f"# Found {len(seg_dicom_files_found)} SEG DICOM input-files!")
        for dcm_file in seg_dicom_files_found:
            compositeContext.append(basename(dcm_file))
        if new_series_number == 1:
            input_dicom = pydicom.dcmread(dcm_file)
            series_number = input_dicom[0x0020, 0x0011].value
            new_series_number = series_number + 2000

    imageLibrary = []
    if src_dicom_operator is not None:
        src_dicom_files_found = glob(join(src_dicom_dir, "*.dcm"), recursive=False)
        print(f"# Found {len(src_dicom_files_found)} SRC DICOM input-files!")
        for dcm_file in src_dicom_files_found:
            imageLibrary.append(basename(dcm_file))

    with open(json_path) as f:
        input_measurements_json = json.load(f)
        if "measurement_groups" not in input_measurements_json:
            print("#")
            print("##################################################")
            print("#")
            print("##################  ERROR  #######################")
            print("#")
            print(f"# measurements-json loaded: {json_path}")
            print("# ----> 'measurement_groups' could not be found !")
            print("#")
            print("# This json is not compatible with this operator -> please have a look at the docs or contact the Kaapana team.")
            print("#")
            print("##################################################")
            print("#")
            exit(1)

    tid_template = {}
    tid_template["@schema"] = "https://raw.githubusercontent.com/qiicr/dcmqi/master/doc/schemas/sr-tid1500-schema.json#"
    tid_template["SeriesNumber"] = str(input_measurements_json["SeriesNumber"]) if "SeriesNumber" in input_measurements_json else str(new_series_number)
    tid_template["SeriesDescription"] = str(input_measurements_json["SeriesDescription"]) if "SeriesDescription" in input_measurements_json else series_description
    tid_template["InstanceNumber"] = str(input_measurements_json["InstanceNumber"]) if "InstanceNumber" in input_measurements_json else f"{processed_count+1}"

    tid_template["compositeContext"] = compositeContext
    tid_template["imageLibrary"] = imageLibrary

    tid_template["observerContext"] = {
        "ObserverType": str(input_measurements_json["ObserverType"]) if "ObserverType" in input_measurements_json else "DEVICE",
        "DeviceObserverName": str(input_measurements_json["DeviceObserverName"]) if "DeviceObserverName" in input_measurements_json else "Kaapana",
        "DeviceObserverManufacturer": str(input_measurements_json["DeviceObserverManufacturer"]) if "DeviceObserverManufacturer" in input_measurements_json else "Kaapana",
        "DeviceObserverUID": str(input_measurements_json["DeviceObserverUID"]) if "DeviceObserverUID" in input_measurements_json else "1.2.3.4.5"  # generate_uid()
    }

    # tid_template["observerContext"] = {
    #     "ObserverType": "PERSON",
    #     "PersonObserverName": "Reader1"
    # },

    # https://dicom.innolitics.com/ciods/basic-text-sr/sr-document-general/0040a493
    tid_template["VerificationFlag"] = str(input_measurements_json["VerificationFlag"]) if "VerificationFlag" in input_measurements_json else "VERIFIED"
    tid_template["CompletionFlag"] = str(input_measurements_json["CompletionFlag"]) if "CompletionFlag" in input_measurements_json else "COMPLETE"
    tid_template["activitySession"] = str(input_measurements_json["activitySession"]) if "activitySession" in input_measurements_json else "1"
    tid_template["timePoint"] = "1"  # should have values of 1 for baseline, and 2 for the followup

    tid_template["Measurements"] = []

    for i, input_measurement_group in enumerate(input_measurements_json["measurement_groups"], start=0):
        measurement_group = {}
        measurement_group["TrackingIdentifier"] = input_measurement_group["TrackingIdentifier"] if "TrackingIdentifier" in input_measurement_group else f"Measurements group {i}"
        measurement_group["ReferencedSegment"] = input_measurement_group["ReferencedSegment"] if "ReferencedSegment" in input_measurement_group else i

        if "SegSeriesFilename" in input_measurement_group:
            if input_measurement_group["SegSeriesFilename"] in tid_template["compositeContext"]:
                dcm_file = join(seg_dicom_dir, input_measurement_group["SegSeriesFilename"])
                seg_series = pydicom.dcmread(dcm_file)
                seg_series_uid = seg_series[0x0008, 0x0018].value
                seg_series_aetitle = seg_series[0x0012, 0x0020].value
                measurement_group["segmentationSOPInstanceUID"] = seg_series_uid
                tid_template["seg_series_aetitle"] = seg_series_aetitle
            else:
                print("#")
                print("##################  ERROR  #######################")
                print("#")
                print(f"# ----> Could not find specified 'SegSeriesFilename':{input_measurement_group['SourceSeriesFilename']} at {seg_dicom_dir} !")
                print("#")
                print("#")
                print("##################################################")
                print("#")
                exit(1)

        if src_dicom_files_found is not None and len(src_dicom_files_found) > 0:
            source_series_uid = pydicom.dcmread(src_dicom_files_found[0])[0x0008, 0x0018].value
            measurement_group["SourceSeriesForImageSegmentation"] = source_series_uid
        else:
            print("#")
            print("##################################################")
            print("#")
            print(f"# --> Could not set 'SourceSeriesForImageSegmentation' -> no src-DICOM found at {src_dicom_dir}")
            print("#")
            print("##################################################")
            print("#")

        if "finding_keyword" in input_measurement_group:
            result = find_code_meaning(input_measurement_group["finding_keyword"])

            measurement_group["Finding"] = {
                "CodeValue": result["Code Value"],
                "CodingSchemeDesignator": result["Coding Scheme Designator"],
                "CodeMeaning": result["Code Meaning"]
            }
        else:
            measurement_group["Finding"] = {}

        if "finding_site_keyword" in input_measurement_group:
            result = find_code_meaning(input_measurement_group["finding_site_keyword"])

            measurement_group["FindingSite"] = {
                "CodeValue": result["Code Value"],
                "CodingSchemeDesignator": result["Coding Scheme Designator"],
                "CodeMeaning": result["Code Meaning"]
            }
        else:
            measurement_group["FindingSite"] = {}

        measurement_group["measurementAlgorithmIdentification"] = {
            "AlgorithmName": input_measurement_group["AlgorithmName"] if "AlgorithmName" in input_measurement_group else "N/A",
            "AlgorithmVersion": input_measurement_group["AlgorithmVersion"] if "AlgorithmVersion" in input_measurement_group else "N/A",
            "AlgorithmParameters": input_measurement_group["AlgorithmParameters"].split(";") if "AlgorithmParameters" in input_measurement_group else ["N/A"],
        }

        measurement_group["measurementItems"] = []
        if "Measurement_list" in input_measurement_group:
            for i, input_measurement in enumerate(input_measurement_group["Measurement_list"], start=0):
                measurement = {}
                assert "value" in input_measurement
                try:
                    value_input = f"{float(input_measurement['value']):.4f}"
                except ValueError:
                    value_input = input_measurement['value']
                measurement["value"] = str(value_input)

                if "quantity" in input_measurement:
                    measurement["quantity"] = input_measurement["quantity"]

                if "units" in input_measurement:
                    measurement["units"] = input_measurement["units"]

                if "derivationModifier" in input_measurement:
                    measurement["derivationModifier"] = input_measurement["derivationModifier"]

                measurement_group["measurementItems"].append(measurement)
        else:
            print("#")
            print("##################################################")
            print("#")
            print(f"# --> Could not find 'Measurement_list' in measurement_group of {json_path}")
            print("#")
            print("##################################################")
            print("#")
        tid_template["Measurements"].append(measurement_group)

    output_meta_json_path = join(json_path.replace(".json", "_tid1500_template.json"))
    with open(output_meta_json_path, "w") as json_output_file:
        json.dump(tid_template, json_output_file, indent=4, sort_keys=False)

    return output_meta_json_path


def process_input_file(inputCompositeContextDirectory, inputImageLibraryDirectory, inputMetadata, output_dicom_path):
    global processed_count, execution_timeout

    command = [
        f"{DCMQI}/tid1500writer",
        "--inputCompositeContextDirectory", inputCompositeContextDirectory,
        "--inputImageLibraryDirectory", inputImageLibraryDirectory,
        "--inputMetadata", inputMetadata,
        "--outputDICOM", output_dicom_path
    ]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=execution_timeout)
    # command stdout output -> output.stdout
    # command stderr output -> output.stderr
    if output.returncode != 0:
        print("#")
        print("##################################################")
        print("#")
        print("##################  ERROR  #######################")
        print("#")
        print("# ----> Something went wrong with the shell-execution!")
        print(f"# Command:  {command}")
        print(f"# json_filepath: {inputMetadata}")
        print(f"# output_dicom_path: {output_dicom_path}")
        print(f"# inputImageLibraryDirectory: {inputImageLibraryDirectory}")
        print(f"# inputCompositeContextDirectory: {inputCompositeContextDirectory}")
        print("#")
        print(f"# STDOUT:")
        print("#")
        for line in output.stdout.split("\\n"):
            print(f"# {line}")
        print("#")
        print("#")
        print("#")
        print("#")
        print(f"# STDERR:")
        print("#")
        for line in output.stderr.split("\\n"):
            print(f"# {line}")
        print("#")
        print("##################################################")
        print("#")
        exit(1)

    print("# Modify DICOM: (0008,0016) => 1.2.840.10008.5.1.4.1.1.88.11")
    dcmseg_file = pydicom.dcmread(output_dicom_path)
    # dcmseg_file[0x0008,0x0016].value = "1.2.840.10008.5.1.4.1.1.88.11" # change Enhanced SR Storage -> Basic Text SR Storage
    dcmseg_file.add_new([0x0008,0x0016], 'UI', "1.2.840.10008.5.1.4.1.1.88.11")

    with open(inputMetadata) as f:
        inputMetadata_dict = json.load(f)
    if "seg_series_aetitle" in inputMetadata_dict:
        aetitle = inputMetadata_dict["seg_series_aetitle"]
        print(f"# Adding aetitle to DICOM SR:   {aetitle}")
        dcmseg_file.add_new([0x012, 0x020], 'LO', aetitle)  # Clinical Trial Protocol ID
    dcmseg_file.save_as(output_dicom_path)

    processed_count += 1
    return True, inputMetadata


DCMQI = '/app/dcmqi/bin'

# DCMQI = '/home/jonas/software/dcmqi/bin'
# os.environ['SRC_DICOM_OPERATOR'] = 'initial-input'
# os.environ['SEG_DICOM_OPERATOR'] = 'None'

# os.environ['BATCH_NAME'] = 'batch'
# os.environ['WORKFLOW_DIR'] = '/home/jonas/Downloads/ukf_test/racoon-ukf-preseg-210625115616399119'
# os.environ['OPERATOR_IN_DIR'] = 'pathonomical-segmentation'
# os.environ['OPERATOR_OUT_DIR'] = 'measurements-sr'
# os.environ['INPUT_FILE_EXTENSION'] = 'volumes.json'

workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None

batch_name = getenv("BATCH_NAME", "None")
batch_name = batch_name if batch_name.lower() != "none" else None
assert batch_name is not None

operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
assert operator_in_dir is not None

operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
assert operator_out_dir is not None

src_dicom_operator = getenv("SRC_DICOM_OPERATOR", "None")
src_dicom_operator = src_dicom_operator if src_dicom_operator.lower() != "none" else None

seg_dicom_operator = getenv("SEG_DICOM_OPERATOR", "None")
seg_dicom_operator = seg_dicom_operator if seg_dicom_operator.lower() != "none" else None

series_description = getenv("SR_SERIES_DESCRIPTION", "Kaapana SR report")

# File-extension to search for in the input-dir
input_file_extension = getenv("INPUT_FILE_EXTENSION", "*.json")
input_file_extension = input_file_extension if input_file_extension.lower() != "none" else None

print("##################################################")
print("#")
print("# Starting operator xyz:")
print("#")
print(f"# workflow_dir:     {workflow_dir}")
print(f"# batch_name:       {batch_name}")
print(f"# operator_in_dir:  {operator_in_dir}")
print(f"# operator_out_dir: {operator_out_dir}")
print("#")
print(f"# src_dicom_operator:    {src_dicom_operator}")
print(f"# seg_dicom_operator:    {seg_dicom_operator}")
print("#")
print("##################################################")
print("#")
print("# Starting processing on BATCH-ELEMENT-level ...")
print("#")
print("##################################################")
print("#")


# Loop for every batch-element (usually series)
batch_folders = sorted([f for f in glob(join('/', workflow_dir, batch_name, '*'))])
for batch_element_dir in batch_folders:
    print("#")
    print(f"# Processing batch-element {batch_element_dir}")
    print("#")
    element_input_dir = join(batch_element_dir, operator_in_dir)
    element_output_dir = join(batch_element_dir, operator_out_dir)

    # check if input dir present
    if not exists(element_input_dir):
        print("#")
        print(f"# Input-dir: {element_input_dir} does not exists!")
        print("# -> skipping")
        print("#")
        continue

    # creating output dir
    Path(element_output_dir).mkdir(parents=True, exist_ok=True)

    json_input_files = glob(join(element_input_dir, input_file_extension), recursive=False)
    print(f"# Found {len(json_input_files)} json input-files!")

    src_dicom_dir = join(batch_element_dir, src_dicom_operator)
    seg_dicom_dir = join(batch_element_dir, seg_dicom_operator) if seg_dicom_operator is not None else join(batch_element_dir, operator_in_dir)

    # Single process:
    # Loop for every input-file found with extension 'input_file_extension'
    for input_file in json_input_files:

        inputMetadata_path = create_measurements_json(
            json_path=input_file,
            src_dicom_dir=src_dicom_dir,
            seg_dicom_dir=seg_dicom_dir
        )

        output_dicom_path = join(element_output_dir, basename(input_file).replace(".json", ".dcm"))
        result, input_file = process_input_file(
            inputCompositeContextDirectory=seg_dicom_dir,
            inputImageLibraryDirectory=src_dicom_dir,
            inputMetadata=inputMetadata_path,
            output_dicom_path=output_dicom_path
        )


print("#")
print("##################################################")
print("#")
print("# BATCH-ELEMENT-level processing done.")
print("#")
print("##################################################")
print("#")

if processed_count == 0:
    print("##################################################")
    print("#")
    print("# -> No files have been processed so far!")
    print("#")
    print("# Starting processing on BATCH-LEVEL ...")
    print("#")
    print("##################################################")
    print("#")

    batch_input_dir = join('/', workflow_dir, operator_in_dir)
    batch_output_dir = join('/', workflow_dir, operator_out_dir)

    json_input_files = glob(join(batch_input_dir, input_file_extension), recursive=False)
    print(f"# Found {len(json_input_files)} json input-files!")

    src_dicom_dir = join(batch_input_dir, src_dicom_operator)
    seg_dicom_dir = join(batch_output_dir, seg_dicom_operator) if seg_dicom_operator is not None else join(batch_output_dir, operator_in_dir)

    # Single process:
    # Loop for every input-file found with extension 'input_file_extension'
    for input_file in json_input_files:
        inputMetadata_path = create_measurements_json(
            json_path=input_file,
            src_dicom_dir=src_dicom_dir,
            seg_dicom_dir=seg_dicom_dir,
        )

        output_dicom_path = join(batch_output_dir, basename(input_file).replace(".json", ".dcm"))
        result, input_file = process_input_file(
            inputCompositeContextDirectory=seg_dicom_dir,
            inputImageLibraryDirectory=src_dicom_dir,
            inputMetadata=inputMetadata_path
        )

    print("#")
    print("##################################################")
    print("#")
    print("# BATCH-LEVEL-level processing done.")
    print("#")
    print("##################################################")
    print("#")

if processed_count == 0:
    print("#")
    print("##################################################")
    print("#")
    print("##################  ERROR  #######################")
    print("#")
    print("# ----> NO FILES HAVE BEEN PROCESSED!")
    print("#")
    print("##################################################")
    print("#")
    exit(1)
else:
    print("#")
    print(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
    print("#")
    print("# DONE #")
