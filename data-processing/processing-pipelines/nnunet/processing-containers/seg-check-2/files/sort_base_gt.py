import os
from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
import logging
from logger_helper import get_logger
import shutil

# For multiprocessing -> usually you should scale via multiple containers!
from multiprocessing.pool import ThreadPool

# For shell-execution
from subprocess import PIPE, run

log_level = getenv("LOG_LEVEL", "info").lower()
log_level_int = None
if log_level == "debug":
    log_level_int = logging.DEBUG
elif log_level == "info":
    log_level_int = logging.INFO
elif log_level == "warning":
    log_level_int = logging.WARNING
elif log_level == "critical":
    log_level_int = logging.CRITICAL
elif log_level == "error":
    log_level_int = logging.ERROR

logger = get_logger(__name__, log_level_int)

execution_timeout = 10

# Counter to check if smth has been processed
processed_count = 0


# Process smth
def process_input_file(filepath):
    global processed_count

    processed_count += 1
    return True, filepath


# Alternative Process smth via shell-command
def process_input_file(filepath):
    global processed_count, execution_timeout

    command = ["echo", "hello world!"]
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


os.environ["WORKFLOW_DIR"] = "/home/jonas/tcia-seg/nnunet-training-230811092330566862/"
os.environ["BATCH_NAME"] = "batch"
os.environ["OPERATOR_IN_DIR"] = "dcm-converter-ct"
os.environ["GT_NIFTI_IN_DIR"] = "mask2nifti"
os.environ["OPERATOR_OUT_DIR"] = "sort-gt-ref"


workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None

batch_name = getenv("BATCH_NAME", "None")
batch_name = batch_name if batch_name.lower() != "none" else None
assert batch_name is not None

operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
assert operator_in_dir is not None

gt_in_dir = getenv("GT_NIFTI_IN_DIR", "None")
gt_in_dir = gt_in_dir if gt_in_dir.lower() != "none" else None
assert gt_in_dir is not None

operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
assert operator_out_dir is not None

move_files = getenv("MOVE_FILES", "False")
move_files = True if move_files.lower() == "true" else False

# File-extension to search for in the input-dir
input_file_extension = "*.nii.gz"

# How many processes should be started?
parallel_processes = 3

print("##################################################")
print("#")
print("# Starting operator xyz:")
print("#")
print(f"# workflow_dir:     {workflow_dir}")
print(f"# batch_name:       {batch_name}")
print(f"# operator_in_dir:  {operator_in_dir}")
print(f"# gt_in_dir:        {gt_in_dir}")
print(f"# operator_out_dir: {operator_out_dir}")
print(f"# move_files:      {move_files}")
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
    element_gt_in_dir = join(batch_element_dir, gt_in_dir)
    element_output_dir = join(batch_element_dir, operator_out_dir)
    batch_output_dir = join("/", workflow_dir, operator_out_dir)

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
    gt_mask_niftis = glob(join(element_gt_in_dir, input_file_extension), recursive=False)
    base_ref_niftis = glob(join(element_input_dir, input_file_extension), recursive=False)
    print(f"# Found {len(base_ref_niftis)} input-files!")
    assert len(base_ref_niftis) == 1
    base_ref_image_uid = basename(base_ref_niftis[0]).replace("nii.gz","")
    gt_target_dir = join(batch_output_dir,base_ref_image_uid)
    Path(gt_target_dir).mkdir(parents=True, exist_ok=True)

    for gt_mask_nifti in gt_mask_niftis:
        target_move_path= join(gt_target_dir,basename(gt_mask_nifti))
        if exists(target_move_path):
            logger.warning(f"Mask {basename(gt_mask_nifti)} already exists in target dir! -> skipping")
            continue

        logger.info(f"Moving {gt_mask_nifti.replace(workflow_dir,'')} -> {target_move_path.replace(workflow_dir,'')} ...")
        shutil.copy2(gt_mask_nifti,target_move_path)
        # shutil.move(gt_mask_nifti,target_move_path)
    
    # Alternative with multi-processing
    # with ThreadPool(parallel_processes) as threadpool:
    #     results = threadpool.imap_unordered(process_input_file, input_files)
    #     for result, input_file in results:
    #         print(f"#  Done: {input_file}")

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
            result, input_file = process_input_file(filepath=input_file)

        # Alternative with multi-processing
        with ThreadPool(parallel_processes) as threadpool:
            results = threadpool.imap_unordered(process_input_file, input_files)
            for result, input_file in results:
                print(f"#  Done: {input_file}")

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
