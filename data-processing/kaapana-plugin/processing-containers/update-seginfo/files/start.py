from os import getenv
from os.path import join, exists
from glob import glob
from logger_helper import get_logger
import logging
import json
from pathlib import Path
import shutil
import nibabel as nib
import numpy as np

processed_count = 0
skip_operator = False
issue_occurred = False
logger = None


def only_update_json(seg_info_list, target_seg_info_dict, label_nifti_path, target_dir):
    '''
    Reads the (multi-label) nifty file, compares to seg_info_list and adds to target_seg_info_dict
    with 'file_found' extra boolean parameter.
    '''
    global processed_count
    nifti_loaded = nib.load(label_nifti_path)
    nifti_numpy = nifti_loaded.get_fdata().astype(int)
    unique_labels = np.unique(nifti_numpy)
    for label_entry in seg_info_list:
        label_int = label_entry["label_int"]
        label_entry["file_found"] = False
        if label_int in unique_labels:
            label_entry["file_found"] = True
        target_seg_info_dict["seg_info"].append(label_entry)
    shutil.copy(label_nifti_path, target_dir)
    processed_count+=1
    return True, target_seg_info_dict


def process_seginfo(nifti_dir, target_dir, mode=None):
    '''
    Reads seg_info json file and calls different functions as per mode.
    Currently only update_json mode is implemented.
    '''
    global processed_count, input_file_extension, skip_operator

    Path(target_dir).mkdir(parents=True, exist_ok=True)

    json_files = glob(join(nifti_dir, "*.json"), recursive=True)
    seg_info_json = [x for x in json_files if "seg_info" in x]

    if len(seg_info_json) == 1:
        with open(seg_info_json[0], "r") as f:
            seg_info_dict = json.load(f)
    else:
        logger.info(f"No valid seg_info json found @{nifti_dir}")
        exit(1)
    # ensure seg_info_list's desired form: [{...}, {...}, {...}]
    if isinstance(seg_info_dict, dict):
        if "seg_info" in seg_info_dict:
            seg_info_list = seg_info_dict["seg_info"]
    else:
        seg_info_list = seg_info_dict

    # define variables for combing or fusing
    target_seg_info_dict = {"seg_info": []}
    logger.info("seg_info loaded:")
    logger.info(json.dumps(seg_info_list, indent=4))

    # get nifti file names
    nifti_search_query = join(nifti_dir, "*.nii.gz")
    logger.info(f"Collecting NIFTIs @{nifti_search_query}")
    input_files = glob(nifti_search_query, recursive=False)
    logger.info(
        f"Found {len(input_files)} NIFTI files vs {len(seg_info_list)} seg infos ..."
    )
    assert len(input_files) > 0

    if mode == "update_json":
        assert len(input_files) == 1
        res, target_seg_info_dict = only_update_json(
            seg_info_list,
            target_seg_info_dict,
            input_files[0],
            target_dir)
    else:
        # given mode is not supported --> through error
        logger.error(f"#")
        logger.error(
            f"# MODE not supported! Choose either mode 'combine' or 'fuse' segmentation label masks!"
        )
        logger.error(f"#")
        exit(1)

    return res, nifti_dir, target_seg_info_dict


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

    mode = getenv("MODE", "None")
    mode = mode if mode.lower() != "none" else None
    assert mode is not None

    logger.info("##################################################")
    logger.info("#")
    logger.info("# Starting UpdateSegInfoJSON operator:")
    logger.info("#")
    logger.info(f"# workflow_dir:     {workflow_dir}")
    logger.info(f"# batch_name:       {batch_name}")
    logger.info(f"# operator_in_dir:  {operator_in_dir}")
    logger.info(f"# operator_out_dir: {operator_out_dir}")
    logger.info(f"# mode: {mode}")
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
            success, nifti_dir, target_seg_info_dict = process_seginfo(
                nifti_dir=element_input_dir,
                target_dir=element_output_dir,
                mode=mode,
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
            # merge masks with mode
            success, nifti_dir, target_seg_info_dict = process_seginfo(
                nifti_dir=batch_input_dir, target_dir=batch_output_dir, mode=mode
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
