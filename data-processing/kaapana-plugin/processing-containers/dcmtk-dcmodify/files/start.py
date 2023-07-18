from os import getenv
from pathlib import Path
import shutil
import pydicom

# For shell-execution
from subprocess import PIPE, run

execution_timeout = 10

# Counter to check if smth has been processed
processed_count = 0


# Alternative Process smth via shell-command
def process_input_file(filepath):
    global processed_count, execution_timeout, dcm_tags_to_modify, new_values

    print(f"# Processing dcm-file: {filepath}")
    command = ["dcmodify"]
    for i, dcm_tag in enumerate(dcm_tags_to_modify, start=0):
        print(f"# Adding tag: {dcm_tag}")
        command.append("-m")
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
print("#")
print("##################################################")
print("#")
print("# Starting processing on BATCH-ELEMENT-level ...")
print("#")
print("##################################################")
print("#")


# Loop for every batch-element (usually series)
batch_folders = sorted(list(Path("/", workflow_dir, batch_name).glob("*")))
for batch_element_dir in batch_folders:
    print("#")
    print(f"# Processing batch-element {batch_element_dir}")
    print("#")
    element_input_dir = batch_element_dir / operator_in_dir
    element_output_dir = batch_element_dir / operator_out_dir

    # check if input dir present
    if not element_input_dir.exists():
        print("#")
        print(f"# Input-dir: {element_input_dir} does not exists!")
        print("# -> skipping")
        print("#")
        continue

    # creating output dir
    element_output_dir.mkdir(parents=True, exist_ok=True)

    # create a list of input files
    input_files = list(
        [
            p
            for p in (element_input_dir).rglob("*")
            if p.is_file() and pydicom.misc.is_dicom(p)
        ]
    )
    print(f"# Found {len(input_files)} input-files!")

    # copy input files to the output directory before processing
    output_files = [
        shutil.copy(input_file, element_output_dir) for input_file in input_files
    ]
    # Single process:
    # Loop for every input-file found
    for output_file in output_files:
        result, output_file = process_input_file(filepath=output_file)


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

    batch_input_dir = Path("/", workflow_dir, operator_in_dir)
    batch_output_dir = Path("/", workflow_dir, operator_in_dir)

    # check if input dir present
    if not batch_input_dir.exists():
        print("#")
        print(f"# Input-dir: {batch_input_dir} does not exists!")
        print("# -> skipping")
        print("#")
    else:
        # creating output dir
        batch_output_dir.mkdir(parents=True, exist_ok=True)

        # creating output dir
        input_files = [
            f
            for f in (batch_input_dir).rglob("*")
            if f.is_file() and pydicom.misc.is_dicom(f)
        ]
        print(f"# Found {len(input_files)} input-files!")

        # Single process:
        # Loop for every input-file found with extension 'input_file_extension'
        for input_file in input_files:
            result, input_file = process_input_file(filepath=input_file)

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
