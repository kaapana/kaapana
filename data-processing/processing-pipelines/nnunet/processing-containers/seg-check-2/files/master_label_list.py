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
os.environ["OPERATOR_IN_DIR"] = "sort-gt-ref"
os.environ["OPERATOR_OUT_DIR"] = "master-label-dict"

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

# File-extension to search for in the input-dir
input_file_extension = "*.nii.gz"


print("##################################################")
print("#")
print("# Starting operator xyz:")
print("#")
print(f"# workflow_dir:     {workflow_dir}")
print(f"# batch_name:       {batch_name}")
print(f"# operator_in_dir:  {operator_in_dir}")
print(f"# operator_out_dir: {operator_out_dir}")
print("#")
print("##################################################")
print("#")
print("# Starting processing on BATCH-ELEMENT-level ...")
print("#")
print("##################################################")
print("#")

master_label_dict = {}

batch_input_dir = join("/", workflow_dir, operator_in_dir)
batch_output_dir = join("/", workflow_dir, operator_in_dir)

assert exists(batch_input_dir)

# creating output dir
Path(batch_output_dir).mkdir(parents=True, exist_ok=True)

# creating output dir
input_files = glob(join(batch_input_dir, input_file_extension), recursive=True)
print(f"# Found {len(input_files)} input-files!")

base_image_dirs = sorted([f for f in glob(join(batch_input_dir, "*"))])
for base_image_dir in base_image_dirs:
    seg_niftis = glob(join(base_image_dir, input_file_extension), recursive=False)
    print(f"# Found {len(seg_niftis)} input-files!")
    for seg_nifti in seg_niftis:
        base_id = basename(seg_nifti).replace(".nii.gz", "")
        assert len(base_id.split("--")) == 3
        integer_encoding = base_id.split("--")[1]
        label_name = base_id.split("--")[2]

        if label_name not in master_label_dict:
            master_label_dict[label_name] = {
                "count": 1,
                "integer_encoding": [integer_encoding],
            }
        else:
            master_label_dict[label_name]["count"] += 1
            master_label_dict[label_name]["integer_encoding"].append(integer_encoding)

sorted_by_occurrence = {k: v for k, v in sorted(master_label_dict.items(), key=lambda item: item[1]["count"],reverse=True)}


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
