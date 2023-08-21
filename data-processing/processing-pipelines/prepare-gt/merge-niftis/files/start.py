import os
import logging
import json
from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
from logger_helper import get_logger
import nibabel as nib
import numpy as np

# For multiprocessing -> usually you should scale via multiple containers!
from multiprocessing.pool import ThreadPool

execution_timeout = 10

# Counter to check if smth has been processed
processed_count = 0


# Process smth
def process_batch_element(batch_element_dir):
    global processed_count, logger, master_label_dict, input_file_extension

    logger.info(f"Starting processing: {basename(batch_element_dir)}")
    try:
        local_seg_dict = {}
        element_input_dir = join(batch_element_dir, operator_in_dir)
        element_output_dir = join(batch_element_dir, operator_out_dir)
        Path(element_output_dir).mkdir(parents=True, exist_ok=True)

        gt_mask_niftis = glob(
            join(element_input_dir, input_file_extension), recursive=False
        )

        merged_mask = None
        for gt_mask_nifti in gt_mask_niftis:
            base_id = basename(gt_mask_nifti).replace(".nii.gz", "")
            assert len(base_id.split("--")) == 3
            integer_encoding = int(base_id.split("--")[1])
            label_name = base_id.split("--")[2]
            logger.debug(f"{integer_encoding=}")
            logger.debug(f"{label_name=}")

            assert label_name in master_label_dict

            if isinstance(master_label_dict[label_name], str):
                target_encoding = master_label_dict[master_label_dict[label_name]]
                new_label_name = master_label_dict[label_name]
            elif isinstance(master_label_dict[label_name], int):
                target_encoding = master_label_dict[label_name]
                new_label_name = label_name
            else:
                logger.error("Something went wrong.")
                exit(1)

            if new_label_name not in local_seg_dict:
                local_seg_dict[new_label_name] = target_encoding

            logger.debug(f"Loading mask {basename(gt_mask_nifti)}")
            mask_loaded = nib.load(gt_mask_nifti)
            logger.debug(f"Loading Nifti ... ")
            mask_numpy = mask_loaded.get_fdata().astype(np.uint8)
            labels_found = list(np.unique(mask_numpy))
            logger.debug(f"mask_numpy labels_found org: {labels_found}")
            assert labels_found == [0, integer_encoding]

            if np.max(mask_numpy) > integer_encoding:
                logger.error(f"{np.max(mask_numpy)}")
                exit(1)

            if merged_mask is None:
                logger.debug(f"Creating empty merge-mask ...")
                merged_mask = np.zeros_like(mask_numpy, dtype=np.uint8)
                affine = mask_loaded.affine
                header = mask_loaded.header
            elif mask_numpy.shape != merged_mask.shape:
                logger.error(
                    f"Shape missmatch: {mask_numpy.shape=} vs {merged_mask.shape=}"
                )
                exit(1)

            logger.debug(
                f"Setting target encoding: {integer_encoding} -> {target_encoding}"
            )
            mask_numpy[mask_numpy == integer_encoding] = target_encoding
            labels_found = list(np.unique(mask_numpy))
            logger.debug(f"mask_numpy labels_found converted: {labels_found}")
            assert labels_found == [0, target_encoding]

            logger.debug(f"Merging masks ... ")
            mask = (merged_mask == 0) & (mask_numpy != 0)
            merged_mask[mask] = mask_numpy[mask]

            labels_found = list(np.unique(merged_mask))
            logger.debug(f"merged_mask labels_found: {labels_found}")

            logger.debug(f"Mask {label_name} done ")

        seg_info = {
            "algorithm": "Mask-Merger",
            "seg_info": [],
        }
        seg_info_path = join(element_output_dir, "seg_info.json")

        logger.debug(f"Generating {seg_info_path} ...")
        for key, value in local_seg_dict.items():
            seg_info["seg_info"].append(
                {
                    "label_name": key,
                    "label_int": str(value),
                }
            )
        with open(seg_info_path, "w") as f:
            json.dump(seg_info, indent=4, fp=f)

        merged_nifti_path = join(element_output_dir, "merged.nii.gz")
        logger.debug(f"Saving merged nifti @ {merged_nifti_path} ...")
        merged_mask_nii = nib.Nifti1Image(merged_mask, affine, header)
        nib.save(merged_mask_nii, merged_nifti_path)

        processed_count += 1
        return basename(batch_element_dir), "success"
    except Exception as e:
        logger.error("Something went wrong!")
        logger.error(e)
        return basename(batch_element_dir), "failed"


# os.environ['WORKFLOW_DIR'] = '/home/jonas/test-data/prepare-gt-230821124942171287/'
# os.environ['BATCH_NAME'] = 'sorted'
# os.environ['OPERATOR_IN_DIR'] = 'mask2nifti'
# os.environ['OPERATOR_OUT_DIR'] = 'merge-masks'

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

log_level = getenv("LOG_LEVEL", "INFO")
log_level = log_level if log_level.lower() != "none" else None
log_level = log_level.lower()
assert log_level is not None

master_label_dict_path = join(
    workflow_dir, "get-master-label-list", "master_label_list.json"
)
assert exists(master_label_dict_path)
with open(master_label_dict_path) as f:
    master_label_dict = json.load(f)

# File-extension to search for in the input-dir
input_file_extension = "*.nii.gz"

# How many processes should be started?
parallel_processes = 3

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
errors = False

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

batch_folders = sorted([f for f in glob(join("/", workflow_dir, batch_name, "*"))])

with ThreadPool(parallel_processes) as threadpool:
    results = threadpool.imap_unordered(process_batch_element, batch_folders)
    for batch_element_dir, result in results:
        print(f"#  {batch_element_dir}: {result}")
        if result != "success":
            errors = True

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

        with ThreadPool(parallel_processes) as threadpool:
            results = threadpool.imap_unordered(
                process_batch_element, [batch_input_dir]
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

if errors:
    exit(1)
