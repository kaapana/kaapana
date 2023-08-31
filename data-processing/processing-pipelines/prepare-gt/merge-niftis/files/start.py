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
import ast

# For multiprocessing -> usually you should scale via multiple containers!
from multiprocessing.pool import ThreadPool

execution_timeout = 10

# Counter to check if smth has been processed
processed_count = 0


# Check for overlap
def check_overlap(mask_numpy, merged_mask):
    overlap_percentage = 0
    overlap_mask = np.logical_and(merged_mask, mask_numpy)
    if np.any(overlap_mask):
        logger.warning(f"The masks have overlapping areas. {overlap_strategie=}")
        unique_values_merge = np.unique(mask_numpy[overlap_mask], return_counts=False)
        overlap_merge_label = [
            k for k, v in master_label_dict.items() if v == max(unique_values_merge)
        ]
        assert len(overlap_merge_label)
        overlap_merge_label = overlap_merge_label[0]

        unique_values_base, counts_base = np.unique(
            merged_mask[overlap_mask], return_counts=True
        )
        for index, overlap_value in enumerate(unique_values_base):
            overlap_base_label = [
                k for k, v in master_label_dict.items() if v == overlap_value
            ]
            assert len(overlap_base_label) == 1
            logger.warning(
                f"{counts_base[index]} overlapping voxels for label '{overlap_base_label[0]}' and '{overlap_merge_label}'"
            )
        if overlap_threshold != 0:
            # Count the overlapping voxels
            overlap_count = np.sum(overlap_mask)
            # Calculate the total number of pixels in either mask (assuming they have the same shape)
            total_voxels = merged_mask.size
            # Calculate the percentage of overlapping voxels
            overlap_percentage = (overlap_count / total_voxels) * 100
            logger.warning(
                f"The percentage of overlapping voxels is: {overlap_percentage:.2f}% vs the theshold: {overlap_threshold}%"
            )
            if overlap_percentage <= overlap_threshold:
                logger.warning(
                    f"-> still ok -> using {overlap_merge_label} -> continue."
                )
                return "ok", mask_numpy, merged_mask

        if overlap_strategie == "skip":
            result = "skip"
        elif overlap_strategie == "crash":
            logger.error(f"Overlap identified -> {overlap_strategie=} -> exit!")
            result = "crash"

        elif overlap_strategie == "set_to_background":
            logger.warning(
                f"Overlap identified -> {overlap_strategie=} -> setting overlapping voxels to 0 !"
            )
            # Create a mask where overlapping pixels are set to False
            no_overlap_mask = np.logical_not(overlap_mask)
            # Zero out the overlapping pixels in both masks using the no_overlap_mask
            merged_mask[no_overlap_mask] = 0
            mask_numpy[no_overlap_mask] = 0
            result = "ok"
        else:
            logger.warning(f"Unknown overlap-strategy: {overlap_strategie} -> exit")
            result = "crash"

    else:
        logger.debug("No overlapping areas found.")
        result = "ok"

    return result, mask_numpy, merged_mask


# Process gt niftis for each base image
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
        if len(seg_order) > 0:
            new_order_gt_mask_niftis = []
            for sort_label in seg_order:
                for gt_mask_nifti in gt_mask_niftis:
                    if sort_label.lower() in basename(gt_mask_nifti).lower():
                        new_order_gt_mask_niftis.append(gt_mask_nifti)
                        break

            if len(gt_mask_niftis) != len(new_order_gt_mask_niftis):
                for gt_mask_nifti in gt_mask_niftis:
                    if gt_mask_nifti not in new_order_gt_mask_niftis:
                        new_order_gt_mask_niftis.insert(0, gt_mask_nifti)

            assert len(gt_mask_niftis) == len(new_order_gt_mask_niftis)
            gt_mask_niftis = new_order_gt_mask_niftis
            logger.debug(f"{gt_mask_niftis=}")

        merged_mask = None
        for gt_mask_nifti in gt_mask_niftis:
            base_id = basename(gt_mask_nifti).replace(".nii.gz", "")
            assert len(base_id.split("--")) == 3
            integer_encoding = int(base_id.split("--")[1])
            label_name = base_id.split("--")[2].lower()
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
                return basename(batch_element_dir), "crash"

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
                return basename(batch_element_dir), "crash"

            logger.debug(
                f"Setting target encoding: {integer_encoding} -> {target_encoding}"
            )
            mask_numpy[mask_numpy == integer_encoding] = target_encoding
            labels_found = list(np.unique(mask_numpy))
            logger.debug(f"mask_numpy labels_found converted: {labels_found}")
            assert labels_found == [0, target_encoding]

            if merged_mask is None:
                logger.debug(f"Creating empty merge-mask ...")
                merged_mask = np.zeros_like(mask_numpy, dtype=np.uint8)
                affine = mask_loaded.affine
                header = mask_loaded.header
            elif mask_numpy.shape != merged_mask.shape:
                logger.error(
                    f"Shape missmatch: {mask_numpy.shape=} vs {merged_mask.shape=}"
                )
                continue
                # return basename(batch_element_dir), "crash"
            elif overlap_strategie != "none":
                result, mask_numpy, merged_mask = check_overlap(
                    merged_mask=merged_mask, mask_numpy=mask_numpy
                )
                if result == "skip":
                    logger.warning(
                        f"Overlap identified -> {overlap_strategie=} -> skipping mask {basename(gt_mask_nifti)} !"
                    )
                    continue
                elif result == "crash":
                    logger.error(
                        f"Overlap identified -> {overlap_strategie=} -> exit !"
                    )
                    continue
                    # return basename(batch_element_dir), "crash"

            logger.debug(f"Merging masks ... ")
            mask = mask_numpy != 0
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
        nib.Nifti1Image(merged_mask, affine, header).to_filename(merged_nifti_path)

        processed_count += 1
        return basename(batch_element_dir), "success"
    except Exception as e:
        logger.error("Something went wrong!")
        logger.error(e)
        return basename(batch_element_dir), "failed"


# os.environ["WORKFLOW_DIR"] = "/home/jonas/test-data/prepare-gt-230821124942171287/"
# os.environ["BATCH_NAME"] = "sorted"
# os.environ["OPERATOR_IN_DIR"] = "mask2nifti"
# os.environ["OPERATOR_OUT_DIR"] = "merge-masks"
# os.environ["PARALLEL_PROCESSES"] = "1"
# os.environ["OVERLAP_STRATEGY"] = "skip"
# os.environ["OVERLAP_THRESHOLD"] = "0.01"
# os.environ[
#     "SEG_ORDER"
# ] = "['lung','neoplasm, primary','spinal-cord','spinal cord','spinal-cord','esophagus','heart']"

overlap_strategies = ["none", "skip", "crash", "set_to_background"]

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

seg_order = getenv("SEG_ORDER", "[]")
seg_order = ast.literal_eval(seg_order)

overlap_strategie = getenv("OVERLAP_STRATEGY", "crash").lower()
parallel_processes = int(getenv("PARALLEL_PROCESSES", "3"))
overlap_threshold = float(getenv("OVERLAP_THRESHOLD", "0"))

master_label_dict_path = join(
    workflow_dir, "get-master-label-list", "master_label_list.json"
)

# File-extension to search for in the input-dir
input_file_extension = "*.nii.gz"

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

logger.info("##################################################")
logger.info("#")
logger.info("# Starting operator mask2nifti:")
logger.info("#")
logger.info(f"# workflow_dir:     {workflow_dir}")
logger.info(f"# batch_name:       {batch_name}")
logger.info(f"# operator_in_dir:  {operator_in_dir}")
logger.info(f"# operator_out_dir: {operator_out_dir}")
logger.info(f"# overlap_strategie:  {overlap_strategie}")
logger.info(f"# overlap_threshold:  {overlap_threshold}")
logger.info(f"# parallel_processes: {parallel_processes}")
logger.info(f"# seg_order:          {seg_order}")
logger.info("#")
logger.info(f"# master_label_dict_path: {master_label_dict_path}")
logger.info("#")
logger.info("##################################################")
logger.info("#")
logger.info("# Starting processing on BATCH-ELEMENT-level ...")
logger.info("#")
logger.info("##################################################")
logger.info("#")

assert exists(master_label_dict_path)
with open(master_label_dict_path) as f:
    master_label_dict = json.load(f)


if overlap_strategie not in overlap_strategies:
    logger.error(f"Overlap strategy: {overlap_strategie} not supported!")
    exit(1)


batch_folders = sorted([f for f in glob(join("/", workflow_dir, batch_name, "*"))])
batch_size = len(batch_folders)
batch_index = 0

with ThreadPool(parallel_processes) as threadpool:
    results = threadpool.imap_unordered(process_batch_element, batch_folders)
    for batch_element_dir, result in results:
        batch_index += 1
        logger.info(f"#  {batch_element_dir}: {result} ({batch_index}/{batch_size})")
        if result == "crash":
            logger.error(f"Error occurred!")
            exit(1)

        elif result != "success":
            errors = True

logger.info("#")
logger.info("##################################################")
logger.info("#")
logger.info("# BATCH-ELEMENT-level processing done.")
logger.info("#")
logger.info("##################################################")
logger.info("#")

if processed_count == 0:
    logger.info("##################################################")
    logger.info("#")
    logger.info("# -> No files have been processed so far!")
    logger.info("#")
    logger.info("# Starting processing on BATCH-LEVEL ...")
    logger.info("#")
    logger.info("##################################################")
    logger.info("#")

    batch_input_dir = join("/", workflow_dir, operator_in_dir)
    batch_output_dir = join("/", workflow_dir, operator_in_dir)

    # check if input dir present
    if not exists(batch_input_dir):
        logger.info("#")
        logger.info(f"# Input-dir: {batch_input_dir} does not exists!")
        logger.info("# -> skipping")
        logger.info("#")
    else:
        # creating output dir
        Path(batch_output_dir).mkdir(parents=True, exist_ok=True)

        with ThreadPool(parallel_processes) as threadpool:
            results = threadpool.imap_unordered(
                process_batch_element, [batch_input_dir]
            )

    logger.info("#")
    logger.info("##################################################")
    logger.info("#")
    logger.info("# BATCH-LEVEL-level processing done.")
    logger.info("#")
    logger.info("##################################################")
    logger.info("#")

if processed_count == 0:
    logger.info("#")
    logger.info("##################################################")
    logger.info("#")
    logger.info("##################  ERROR  #######################")
    logger.info("#")
    logger.info("# ----> NO FILES HAVE BEEN PROCESSED!")
    logger.info("#")
    logger.info("##################################################")
    logger.info("#")
    exit(1)
else:
    logger.info("#")
    logger.info(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
    logger.info("#")
    logger.info("# DONE #")

if errors:
    exit(1)
