from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
from logger_helper import get_logger
import logging
import json
import shutil
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
import shutil
import nibabel as nib
import numpy as np
import json

input_file_extension = "*.nii.gz"
processed_count = 0
issue_occurred = False
logger = None


def combine_mask_nifits(nifti_dir, target_dir):
    global processed_count, input_file_extension

    Path(target_dir).mkdir(parents=True, exist_ok=True)
    target_nifti_path = join(target_dir, "combined_masks.nii.gz")
    seg_info_path = join(nifti_dir, "seg_info.json")
    base_img = None
    base_img_numpy = None
    base_img_labels = None
    logger.info(f"seg_info JSON @{seg_info_path}")
    target_seg_info_dict = {"seg_info": []}
    assert exists(seg_info_path)
    with open(seg_info_path, "r") as f:
        seg_info_dict = json.load(f)["seg_info"]
    logger.info("seg_info loaded:")
    logger.info(json.dumps(seg_info_dict, indent=4))

    nifti_search_query = join(nifti_dir, "*.nii.gz")
    logger.info(f"Collecting NIFTIs @{nifti_search_query}")
    input_files = glob(nifti_search_query, recursive=True)
    logger.info(f"Found {len(input_files)} NIFTI files ...")
    assert len(input_files) > 0
    assert len(input_files) <= len(seg_info_dict)

    if len(seg_info_dict) == 1:
        logger.info("Only one label present -> no merging required.")
        assert len(input_files) == 1
        nifti_loaded = nib.load(input_files[0])
        nifti_numpy = nifti_loaded.get_fdata().astype(int)
        nifti_labels_found = list(np.unique(nifti_numpy))
        logger.info(f"{ nifti_labels_found= }")
        assert len(nifti_labels_found) > 1
        shutil.copy(input_files[0], target_nifti_path)
        target_seg_info_dict["seg_info"].append(seg_info_dict[0])
        processed_count += 1
        return True, nifti_dir

    input_files = glob(join(nifti_dir, input_file_extension), recursive=True)

    for label_entry in seg_info_dict:
        label_name = label_entry["label_name"]
        label_int = label_entry["label_int"]
        label_nifti_path = join(nifti_dir, f"{label_name}.nii.gz")
        if not exists(label_nifti_path):
            logger.warning("")
            logger.warning("")
            logger.warning("")
            logger.warning(
                f"Segmentation {basename(label_nifti_path)} does not exist -> skipping ..."
            )
            logger.warning("")
            logger.warning("")
            logger.warning("")
            continue
        logger.info("")
        logger.info("")
        logger.info(f"Merging {basename(label_nifti_path)}")
        nifti_loaded = nib.load(label_nifti_path)
        nifti_numpy = nifti_loaded.get_fdata().astype(int)

        nifti_numpy[nifti_numpy == 1] = label_int
        nifti_labels_found = list(np.unique(nifti_numpy))
        logger.info(f"New labels found {nifti_labels_found}")
        if len(nifti_labels_found) == 1:
            logger.warning("No annotation has been found -> skipping mask ...")
            continue

        if base_img == None:
            base_img = nifti_loaded
            base_img_numpy = nifti_numpy
            base_img_labels = nifti_labels_found
            logger.info(f"Set base_img with labels: {base_img_labels}")
            processed_count += 1
            target_seg_info_dict["seg_info"].append(label_entry)
            continue

        if base_img.shape != nifti_loaded.shape:
            logger.error("")
            logger.error(basename(label_nifti_path))
            logger.error("Shape miss-match! -> Error")
            logger.error("")
            exit(1)

        duplicates_found = [
            x for x in nifti_labels_found if x != 0 and x in base_img_labels
        ]
        for duplicate in duplicates_found:
            logger.error("")
            logger.error(f"Label {duplicate} has already been found! -> Error")
            logger.error("")
        else:
            logger.info("No duplicates found.")

        if len(duplicates_found) > 0:
            exit(1)

        overlap_percentage = check_overlap(base_map=base_img_numpy, new_map=nifti_numpy)
        if overlap_percentage > 0:
            logger.error("")
            logger.error(label_nifti_path)
            logger.error(
                f"Overlap ({overlap_percentage} %) has been identified! -> copy org nifti"
            )
            logger.error("")
            # keep_nifti_path = join(target_dir, basename(label_nifti_path))
            # keep_nifti = nib.Nifti1Image(nifti_numpy, base_img.affine, base_img.header)
            # keep_nifti.to_filename(keep_nifti_path)
            continue

        logger.info(" -> no overlap ♥")
        logger.info(" Merging base_img_numpy + nifti_numpy ...")
        logger.info("")
        base_img_numpy = np.maximum(base_img_numpy, nifti_numpy)
        base_img_labels = list(np.unique(base_img_numpy))
        target_seg_info_dict["seg_info"].append(label_entry)
        processed_count += 1

    logger.info(f" Generating merged result NIFTI @{basename(target_nifti_path)}")
    assert len(base_img_labels) > 1
    result_nifti = nib.Nifti1Image(base_img_numpy, base_img.affine, base_img.header)
    result_nifti.to_filename(target_nifti_path)
    logger.info(f"Done {processed_count=}")

    return True, nifti_dir, target_seg_info_dict


def check_overlap(base_map, new_map):
    overlap_percentage = 0

    base_map = np.where(base_map != 0, 1, base_map)
    new_map = np.where(new_map != 0, 1, new_map)

    agg_arr = base_map + new_map
    max_value = int(np.amax(agg_arr))
    if max_value > 1:
        overlap_indices = agg_arr > 1
        overlap_voxel_count = overlap_indices.sum()
        overlap_percentage = 100 * float(overlap_voxel_count) / float(base_map.size)

    return overlap_percentage


if __name__ == "__main__":
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

    logger.info("##################################################")
    logger.info("#")
    logger.info("# Starting combine-masks operator:")
    logger.info("#")
    logger.info(f"# workflow_dir:     {workflow_dir}")
    logger.info(f"# batch_name:       {batch_name}")
    logger.info(f"# operator_in_dir:  {operator_in_dir}")
    logger.info(f"# operator_out_dir: {operator_out_dir}")
    logger.info("#")
    logger.info("#")
    logger.info("##################################################")
    logger.info("#")
    logger.info("# Starting processing on BATCH-ELEMENT-level ...")
    logger.info("#")
    logger.info("##################################################")
    logger.info("#")

    # Loop for every batch-element (usually series)
    batch_folders = sorted([f for f in glob(join("/", workflow_dir, batch_name, "*"))])
    for batch_element_dir in batch_folders:
        logger.info("#")
        logger.info(f"# Processing batch-element {batch_element_dir}")
        logger.info("#")
        element_input_dir = join(batch_element_dir, operator_in_dir)
        element_output_dir = join(batch_element_dir, operator_out_dir)

        # check if input dir present
        if not exists(element_input_dir):
            logger.info("#")
            logger.info(f"# Input-dir: {element_input_dir} does not exists!")
            logger.info("# -> skipping")
            logger.info("#")
            continue
        else:
            success, nifti_dir, target_seg_info_dict = combine_mask_nifits(
                nifti_dir=element_input_dir, target_dir=element_output_dir
            )
            target_seg_info_path = join(element_output_dir, "seg_info.json")
            assert not exists(target_seg_info_path)
            with open(target_seg_info_path, "w") as fp:
                json.dump(target_seg_info_dict, fp, indent=4)

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
            success, nifti_dir, target_seg_info_dict = combine_mask_nifits(
                nifti_dir=batch_input_dir, target_dir=batch_output_dir
            )
            target_seg_info_path = join(batch_output_dir, "seg_info.json")
            assert not exists(target_seg_info_path)
            with open(target_seg_info_path, "w") as fp:
                json.dump(target_seg_info_dict, fp, indent=4)

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
        if issue_occurred:
            logger.info("#")
            logger.info("##################################################")
            logger.info("#")
            logger.info("# There were some issues!")
            logger.info("#")
            logger.info("##################################################")
            logger.info("#")
        exit(1)
    else:
        logger.info("#")
        logger.info(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
        logger.info("#")
        logger.info("# DONE #")
