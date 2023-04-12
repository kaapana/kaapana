from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
import shutil
import nibabel as nib
import numpy as np
import json
import logging
from os import getenv
from multiprocessing.pool import ThreadPool
from logger_helper import get_logger

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


def combine_mask_nifits(nifti_dir, target_dir):
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    target_nifti_path = join(target_dir, "combined_total_segmentator.nii.gz")
    seg_info_path = join(nifti_dir, "seg_info.json")
    target_seg_info_path = join(target_dir, "seg_info.json")
    processed_count = 0
    base_img = None
    base_img_numpy = None
    base_img_labels = None
    logger.info(f"seg_info JSON @{seg_info_path}")
    assert exists(seg_info_path)
    with open(seg_info_path, "r") as f:
        seg_info_dict = json.load(f)["seg_info"]
    shutil.copy(seg_info_path, target_seg_info_path)
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
        return 1

    for label_entry in seg_info_dict:
        label_name = label_entry["label_name"]
        label_int = label_entry["label_int"]
        label_nifti_path = join(nifti_dir,f"{label_name}.nii.gz")
        assert exists(label_nifti_path)
        logger.info("")
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
            keep_nifti_path = join(target_dir, basename(nifti_path))
            keep_nifti = nib.Nifti1Image(nifti_numpy, base_img.affine, base_img.header)
            keep_nifti.to_filename(keep_nifti_path)
            continue

        logger.info(" -> no overlap ♥")
        logger.info(" Merging base_img_numpy + nifti_numpy ...")
        logger.info("")
        base_img_numpy = np.maximum(base_img_numpy, nifti_numpy)
        base_img_labels = list(np.unique(base_img_numpy))
        processed_count += 1

    logger.info(f" Generating merged result NIFTI @{basename(target_nifti_path)}")
    assert len(base_img_labels) > 1
    result_nifti = nib.Nifti1Image(base_img_numpy, base_img.affine, base_img.header)
    result_nifti.to_filename(target_nifti_path)
    logger.info("Done.")

    return processed_count


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
