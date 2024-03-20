from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
from logger_helper import get_logger
import logging
import json
import shutil
from glob import glob
from pathlib import Path
import shutil
import nibabel as nib
import numpy as np
import json
import re

import cc3d

processed_count = 0
logger = None


def compute_cca(seg_data, connectivity):
    # perform cca
    # returns label_out: np.array of same size as seg_data with a unique cc_id per cc
    # returns N: number of connected components (cc)
    labels_out, N = cc3d.connected_components(seg_data, return_N=True, connectivity=26)

    # component_volumes = {cc_id: num_voxels_in_labels_out==ccid}
    component_volumes = {}
    for cc_id in range(0, N):
        component_volumes[cc_id] = int(np.sum(labels_out == cc_id))

    return component_volumes


def cca(nifti_dir, json_dir, connectivity=26):
    global processed_count
    res_cca = {"connected_component_analysis": {}}

    # get nifti file names
    nifti_files = glob(join(nifti_dir, "*.nii.gz"), recursive=True)

    for nifti_file in nifti_files:
        # load pixel_array of nifti_file to np.array
        nifti = nib.load(nifti_file)
        nifti_numpy = nifti.get_fdata().astype(int)

        # compute cca
        res_cca_from_nifti = compute_cca(nifti_numpy, connectivity)
        res_cca["connected_component_analysis"][
            basename(nifti_file)
        ] = res_cca_from_nifti

        processed_count += 1

    return True, res_cca


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

    json_info_dir = getenv("JSON_INFO_DIR", "None")
    json_info_dir = json_info_dir if json_info_dir.lower() != "none" else None
    assert json_info_dir is not None

    connectivity = getenv("CONNECTIVITY", "None")
    connectivity = connectivity if connectivity.lower() != "none" else None
    assert connectivity is not None

    logger.info("##################################################")
    logger.info("#")
    logger.info("# Starting merge-masks operator:")
    logger.info("#")
    logger.info(f"# workflow_dir:     {workflow_dir}")
    logger.info(f"# batch_name:       {batch_name}")
    logger.info(f"# operator_in_dir:  {operator_in_dir}")
    logger.info(f"# operator_out_dir: {operator_out_dir}")
    logger.info(f"# json_info_dir: {json_info_dir}")
    logger.info(f"# connectivity: {connectivity}")
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
        Path(element_output_dir).mkdir(parents=True, exist_ok=True)

        # check if input dir present
        if not exists(element_input_dir):
            logger.info("#")
            logger.info(f"# Input-dir: {element_input_dir} does not exists!")
            logger.info("# -> skipping")
            logger.info("#")
            continue
        else:
            # prepare and compute cca
            success, res_dict = cca(
                nifti_dir=element_input_dir,
                json_dir=json_info_dir,
                connectivity=connectivity,
            )

            # integrate res_dict into json in json_info_dir
            if json_info_dir:
                # get existing json_info form json_info operator to correct format
                json_info = list(Path(batch_element_dir, json_info_dir).glob("*.json"))
                if len(json_info) > 0:
                    json_info = json_info[0]
                else:
                    logger.info("#")
                    logger.info(
                        f"# No JSON file in {json_info_dir}! ==> No SEG file, so skip!"
                    )
                    logger.info("#")
                    continue

                with open(json_info, "r") as f:
                    json_content = json.load(f)

                # add cca results to existing json_info
                json_content.update(res_dict)

                # save updates json
                with open(join(element_output_dir, basename(json_info)), "w") as fp:
                    json.dump(json_content, fp, indent=4)

            # no existing json_info, just save cca res_dict to output_dir
            else:
                with open(join(element_output_dir, "cca.json"), "w") as fp:
                    json.dump(res_dict, fp, indent=4)

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
        Path(batch_output_dir).mkdir(parents=True, exist_ok=True)

        # check if input dir present
        if not exists(batch_input_dir):
            logger.info("#")
            logger.info(f"# Input-dir: {batch_input_dir} does not exists!")
            logger.info("# -> skipping")
            logger.info("#")
        else:
            # prepare and compute cca
            success, res_dict = cca(
                nifti_dir=batch_input_dir,
                json_dir=json_info_dir,
                connectivity=connectivity,
            )

            # integrate res_dict into json in json_info_dir
            if json_info_dir:
                # get existing json_info form json_info operator to correct format
                json_info = list(Path(batch_input_dir, json_info_dir).glob("*.json"))[0]
                with open(json_info, "r") as f:
                    json_content = json.load(f)

                # add cca results to existing json_info
                json_content.update(res_dict)

                # save updates json
                with open(join(batch_output_dir, basename(json_info)), "w") as fp:
                    json.dump(json_content, fp, indent=4)

            # no existing json_info, just save cca res_dict to output_dir
            else:
                with open(join(batch_output_dir, "cca.json"), "w") as fp:
                    json.dump(res_dict, fp, indent=4)

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
