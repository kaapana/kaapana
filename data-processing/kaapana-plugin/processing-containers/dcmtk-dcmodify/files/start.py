import os
from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
import shutil

# For shell-execution
from subprocess import PIPE, run

execution_timeout = 10

# Counter to check if smth has been processed
processed_count = 0


# Alternative Process smth via shell-command
def process_input_file(filepath, mode):
    global processed_count, execution_timeout, dcm_tags_to_modify, new_values

    print(f"# Processing dcm-file: {filepath}")
    command = ["dcmodify"]
    for i, dcm_tag in enumerate(dcm_tags_to_modify, start=0):
        print(f"# Adding tag: {dcm_tag}")
        if mode == "modify":
            command.append("-m")
        elif mode == "insert":
            command.append("-i")
        else:
            print("#")
            print("##################  ERROR  #######################")
            print("#")
            print("# Specify either 'insert' or 'modify' as valid modes for dcmodify!")
            print(f"Given mode: {mode}")
            print("#")
            exit(1)
        # safe to not do a backup since we already have it in the operator_input_dir
        command.append("--no-backup")
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

dcm_tags_to_modify = dcm_tags_to_modify.split(";")

mode = getenv("MODE", "None")
mode = mode if mode.lower() != "none" else None
assert mode is not None


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
        result, input_file = process_input_file(filepath=input_file, mode=mode)


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
            result, input_file = process_input_file(filepath=input_file, mode=mode)

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
