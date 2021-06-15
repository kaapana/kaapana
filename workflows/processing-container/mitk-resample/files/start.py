import os
from os import getenv, remove
from os.path import join, exists, dirname, basename
from glob import glob
from shutil import copy2, move, rmtree
from pathlib import Path
import nibabel as nib

# For multiprocessing
from multiprocessing.pool import ThreadPool

# For shell-execution
from subprocess import PIPE, run
execution_timeout = 10

# Counter to check if smth has been processed
processed_count = 0

def process_input_file(input_path, original_path, original_shape, target_dir):
    global processed_count, execution_timeout, executable, interpolator, copy_target_data
    print("#")
    print("##################################################")
    print("#")
    print(f"# Resampling:")
    print("#")
    print(f"# input-file: {input_path}")
    print(f"# org-file:   {original_path}")
    result = True
    target_path = join(target_dir, basename(input_path))
    input_shape = nib.load(input_path).shape

    if input_shape != original_shape:
        print("#")
        print("# -> shapes are different!")
        print("#")
        print(f"# input_shape:    {input_shape}")
        print(f"# original_shape: {original_shape}")
        print("#")
        print("# -> starting resampling ...")
        print("#")

        command = [str(executable), "-f", str(original_path), "-m", str(input_path), "-o", str(target_path), "--interpolator", str(interpolator)]
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
            print("#")
            print(f"# STDERR: {output.stderr}")
            print("#")
            print("##################################################")
            print("#")
            result = False
    else:
        print("#")
        print("# -> shapes are already fine!")
        print("# -> skipping...")
        print("#")
        if input_path != target_path:
            print("# -> copy input to target")
            copy2(input_path, target_path)

    if not copy_target_data and result and input_path != target_path:
        print("#")
        print("# -> deleting input file ...")
        print("#")
        remove(input_file)

    print(f"# {basename(input_path)} done.")
    print("#")
    processed_count += 1
    return result, input_file


workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None

batch_name = getenv("BATCH_NAME", "None")
batch_name = batch_name if batch_name.lower() != "none" else None
assert batch_name is not None

operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
assert operator_in_dir is not None

org_input_dir = getenv("ORG_IMG_IN_DIR", "None")
org_input_dir = org_input_dir if org_input_dir.lower() != "none" else None
assert org_input_dir is not None

operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
assert operator_out_dir is not None

copy_target_data = getenv("COPY_DATA", "False")
copy_target_data = True if copy_target_data.lower() == "true" else False

executable = getenv("EXECUTABLE", "None")
executable = executable if executable.lower() != "none" else None
assert executable is not None

# 0=linear (default), 1=nearest neighbor, 2=sinc (optional), (default: 0), Type: Int
interpolator = getenv("INTERPOLATOR", "None")
interpolator = int(interpolator) if interpolator.lower() != "none" else 1

# File-extension to search for in the input-dir
input_file_extension = "*.nii.gz"

# How many processes should be started?
parallel_processes = 3

print("##################################################")
print("#")
print("# Starting resampling:")
print("#")
print(f"# workflow_dir:     {workflow_dir}")
print(f"# batch_name:       {batch_name}")
print(f"# operator_in_dir:  {operator_in_dir}")
print(f"# operator_out_dir: {operator_out_dir}")
print(f"# copy_target_data: {copy_target_data}")
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
    print("####################################################################################################")
    print("#")
    print("#")
    print(f"# Processing batch-element {batch_element_dir}")
    print("#")

    element_input_dir = join(batch_element_dir, operator_in_dir)
    element_output_dir = join(batch_element_dir, operator_out_dir)
    element_org_input_dir = join(batch_element_dir, org_input_dir)

    # check if input dir present
    if not exists(element_input_dir):
        print("#")
        print(f"# Input-dir: {element_input_dir} does not exists!")
        print("# -> skipping")
        print("#")
        continue

    # creating output dir
    Path(element_output_dir).mkdir(parents=True, exist_ok=True)

    # creating output dir
    input_files = glob(join(element_input_dir, input_file_extension), recursive=False)
    original_files = glob(join(element_org_input_dir, input_file_extension), recursive=False)
    assert len(original_files) == 1
    original_path = original_files[0]
    original_shape = nib.load(original_path).shape

    print(f"# Found {len(input_files)} input-files!")
    for input_file in input_files:
        result, input_file = process_input_file(
            input_path=input_file,
            original_path=original_path,
            original_shape=original_shape,
            target_dir=element_output_dir
        )
    print("#")
    print("####################################################################################################")
    print("#")

    # Alternative with multi-processing
    # results = ThreadPool(parallel_processes).imap_unordered(process_input_file, input_files)
    # for result, input_file in results:
    #     print(f"#  Done: {input_file}")
    print(f"# Batch-element {batch_element_dir} done.")

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
    batch_output_dir = join('/', workflow_dir, operator_in_dir)
    batch_org_input_dir = join('/', workflow_dir, org_input_dir)

    # check if input dir present
    if not exists(batch_input_dir):
        print("#")
        print(f"# Input-dir: {batch_input_dir} does not exists!")
        print("# -> skipping")
        print("#")
    else:
        # creating output dir
        Path(batch_output_dir).mkdir(parents=True, exist_ok=True)

        input_files = glob(join(batch_input_dir, input_file_extension), recursive=False)
        original_files = glob(join(batch_org_input_dir, input_file_extension), recursive=False)
        assert len(original_files) == 1

        original_path = original_files[0]
        original_shape = nib.load(original_path).shape

        print(f"# Found {len(input_files)} input-files!")
        for input_file in input_files:
            result, input_file = process_input_file(
                input_path=input_file,
                original_path=original_path,
                original_shape=original_shape,
                target_dir=element_output_dir
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
    print("# DONE #")
