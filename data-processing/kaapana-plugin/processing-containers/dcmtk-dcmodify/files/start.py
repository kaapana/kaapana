import os
from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
import shutil
import pydicom

# For shell-execution
from subprocess import PIPE, run

execution_timeout = 10

# Counter to check if smth has been processed
processed_count = 0


def overwrite(dcm_tags_to_modify, gt_dcm_operator_in_dir, filepath):
    # search gt_dcm_file and read it in
    gt_dcm_files = glob(os.path.join(gt_dcm_operator_in_dir, "*.dcm"))
    gt_dcm = pydicom.dcmread(gt_dcm_files[0])

    # load to-be-overwritten dcm file
    mod_dcm = pydicom.dcmread(filepath)

    for dcm_tag_to_modify in dcm_tags_to_modify:
        # extract dcm_tag -> dcm_tag_keyword -> dcm_tag_val
        dcm_tag_to_modify = dcm_tag_to_modify.split("=")
        dcm_tag = dcm_tag_to_modify[0].strip("(),").replace(",", "")
        dcm_tag_keyword = pydicom.datadict.keyword_for_tag(int(dcm_tag, 16))
        dcm_tag_val = gt_dcm[dcm_tag_keyword]

        # overwrite dcm_tag and val of mod_dcm with dcm_tag and val of gt_dcm
        mod_dcm[dcm_tag_keyword] = dcm_tag_val

    # save mod_dcm with overwritten dcm_tags
    mod_dcm.save_as(filepath)


def insert(dcm_tags_to_modify, filepath):
    # load to-be-overwritten dcm file
    mod_dcm = pydicom.dcmread(filepath)

    for dcm_tag_to_modify in dcm_tags_to_modify:
        # extract dcm_tag -> dcm_tag_keyword -> dcm_tag_val
        dcm_tag_to_modify = dcm_tag_to_modify.split("=")
        dcm_tag = dcm_tag_to_modify[0].strip("(),").replace(",", "")
        dcm_tag_keyword = pydicom.datadict.keyword_for_tag(int(dcm_tag, 16))
        dcm_tag = pydicom.datadict.tag_for_keyword(dcm_tag_keyword)
        if dcm_tag_to_modify[1] == "0.0000.0000.000":
            # special case for tag ImagePositionPatient
            dcm_tag_to_modify[1] = "0.000\\0.000\\0.000"
        dcm_tag_val = pydicom.DataElement(dcm_tag, "LO", dcm_tag_to_modify[1])

        # overwrite dcm_tag and val of mod_dcm with dcm_tag and val of gt_dcm
        mod_dcm[dcm_tag_keyword] = dcm_tag_val

    # save mod_dcm with overwritten dcm_tags
    mod_dcm.save_as(filepath)


# Alternative Process smth via shell-command
def process_input_file(filepath, mode, gt_dcm_operator_in_dir):
    global processed_count, execution_timeout, dcm_tags_to_modify

    # "overwrite" is a pydicom functionality
    if mode == "overwrite":
        overwrite(dcm_tags_to_modify, gt_dcm_operator_in_dir, filepath)

    elif mode == "insert":
        insert(dcm_tags_to_modify, filepath)

    # "insert" and "modify" are dcmodify functionalities
    elif mode == "modify":
        print(f"# Processing dcm-file: {filepath}")
        command = ["dcmodify"]
        # safe to not do a backup since we already have it in the operator_input_dir
        command.append("--no-backup")
        for i, dcm_tag in enumerate(dcm_tags_to_modify, start=0):
            print(f"# Adding tag: {dcm_tag}")
            if mode == "modify":
                command.append("-m")
            elif mode == "insert":
                print("#")
                print(
                    "# WARNING: mode INSERT will overwrite eventually present DICOM tags!"
                )
                print("#")
                command.append("-i")
            else:
                print("#")
                print("##################  ERROR  #######################")
                print("#")
                print(
                    "# Specify either 'insert' or 'modify' as valid modes for dcmodify!"
                )
                print(f"Given mode: {mode}")
                print("#")
                exit(1)
            command.append(dcm_tag)

        command.append(filepath)
        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=execution_timeout,
        )
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
            print(f"# Filepath: {filepath}")
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
            return False, filepath

    processed_count += 1
    return True, filepath


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

dcm_tags_to_modify = getenv("DICOM_TAGS_TO_MODIFY", "None")
dcm_tags_to_modify = (
    dcm_tags_to_modify if dcm_tags_to_modify.lower() != "none" else None
)
assert dcm_tags_to_modify is not None

mode = getenv("MODE", "None")
mode = mode if mode.lower() != "none" else None
assert mode is not None

gt_dcm_operator_in_dir = getenv("GT_DICOM_OPERATOR", "None")
gt_dcm_operator_in_dir = (
    gt_dcm_operator_in_dir if gt_dcm_operator_in_dir.lower() != "none" else None
)
if mode == "overwrite":
    # for mode "overwrite" there has to be a gt_dcm_operator specified
    assert gt_dcm_operator_in_dir is not None
    gt_dcm_operator_in_dir = os.path.join(
        workflow_dir, batch_name, "*", gt_dcm_operator_in_dir
    )

# prepare dcm_tags_to_modify
# split string into list
dcm_tags_to_modify = dcm_tags_to_modify.split(";")
temp_dcm_tags_to_modify = []
for dcm_tag_to_modify in dcm_tags_to_modify:
    dcm_tag_to_modify = dcm_tag_to_modify.split("=")
    dcm_tag = dcm_tag_to_modify[0]
    modified_value = dcm_tag_to_modify[1]
    # change key-word RANDOM_UID to actual random uid
    if modified_value == "RANDOM_UID":
        modified_value = pydicom.uid.generate_uid()
    temp_dcm_tags_to_modify.append(f"{dcm_tag}={modified_value}")
dcm_tags_to_modify = temp_dcm_tags_to_modify


# File-extension to search for in the input-dir
input_file_extension = "*.dcm"

# How many processes should be started?
parallel_processes = 3

print("##################################################")
print("#")
print("# Starting operator xyz:")
print("#")
print(f"# workflow_dir:     {workflow_dir}")
print(f"# batch_name:       {batch_name}")
print(f"# operator_in_dir:  {operator_in_dir}")
print(f"# operator_out_dir: {operator_out_dir}")
print("#")
print(f"# dcm_tags_to_modify: {dcm_tags_to_modify}")
print(f"# dcmodify mode: {mode}")
print("#")
print("##################################################")
print("#")
print("# Starting processing on BATCH-ELEMENT-level ...")
print("#")
print("##################################################")
print("#")

# Loop for every batch-element (usually series)
batch_folders = sorted([f for f in glob(join("/", workflow_dir, batch_name, "*"))])
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

    # copy content from operator_in_dir to operator_out_dir
    # Note: this is necessary since dcmodify modifies existing DICOM file, but we want to preserve original DICOM file
    # Remove the destination directory if it exists
    shutil.rmtree(element_output_dir, ignore_errors=True)
    # Copy the contents of the source directory to the destination directory
    shutil.copytree(element_input_dir, element_output_dir)

    # find to-be-processed files
    input_files = glob(join(element_output_dir, input_file_extension), recursive=True)
    print(f"# Found {len(input_files)} input-files!")

    # Single process:
    # Loop for every input-file found with extension 'input_file_extension'
    for input_file in input_files:
        result, input_file = process_input_file(
            filepath=input_file,
            mode=mode,
            gt_dcm_operator_in_dir=gt_dcm_operator_in_dir,
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

    batch_input_dir = join("/", workflow_dir, operator_in_dir)
    batch_output_dir = join("/", workflow_dir, operator_in_dir)

    # check if input dir present
    if not exists(batch_input_dir):
        print("#")
        print(f"# Input-dir: {batch_input_dir} does not exists!")
        print("# -> skipping")
        print("#")
    else:
        # creating output dir
        Path(batch_output_dir).mkdir(parents=True, exist_ok=True)

        # creating output dir
        input_files = glob(join(batch_input_dir, input_file_extension), recursive=True)
        print(f"# Found {len(input_files)} input-files!")

        # Single process:
        # Loop for every input-file found with extension 'input_file_extension'
        for input_file in input_files:
            result, input_file = process_input_file(
                filepath=input_file,
                mode=mode,
                gt_dcm_operator_in_dir=gt_dcm_operator_in_dir,
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
