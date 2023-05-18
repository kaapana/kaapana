import os
import pydicom
from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
from dcmconverter.rtstruct2nifti import convert_rtstruct
from dcmconverter.dcmseg2nifti import convert_dcmseg
from dcmconverter.logger import get_logger
import logging
from multiprocessing.pool import ThreadPool

logger = get_logger(__name__, logging.DEBUG)

execution_timeout = 10

# Counter to check if smth has been processed
processed_count = 0


def process_input_file(paras):
    global processed_count
    element_mask_dicom, element_base_dicom_in_dir, output_path, seg_filter = paras

    dcm_modality = pydicom.dcmread(element_mask_dicom)[0x0008, 0x0060].value
    if dcm_modality.lower() == "seg":
        logger.info(f"# {element_mask_dicom}: SEG")
        success = convert_dcmseg(
            element_mask_dicom=element_mask_dicom,
            element_base_dicom_in_dir=element_base_dicom_in_dir,
            output_path=output_path,
            seg_filter=seg_filter,
        )
    elif dcm_modality.lower() == "rtstruct":
        logger.info(f"# {element_mask_dicom}: RTSTRUCT")
        assert base_dicom_in_dir is not None
        success = convert_rtstruct(
            element_mask_dicom=element_mask_dicom,
            element_base_dicom_in_dir=element_base_dicom_in_dir,
            output_path=output_path,
            seg_filter=seg_filter,
        )
    else:
        logger.error(f"# Unsupported modality: {dcm_modality}")
        success = False
        return success, element_mask_dicom

    processed_count += 1
    return success, element_mask_dicom


workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None

batch_name = getenv("BATCH_NAME", "None")
batch_name = batch_name if batch_name.lower() != "none" else None
assert batch_name is not None

seg_filter = os.environ.get("SEG_FILTER", "")
if seg_filter != "":
    seg_filter = seg_filter.lower().replace(" ", "").split(",")
    logger.info(f"Set filters: {seg_filter}")
else:
    seg_filter = None

operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
assert operator_in_dir is not None

base_dicom_in_dir = getenv("BASE_DICOM_DIR", "None")
base_dicom_in_dir = base_dicom_in_dir if base_dicom_in_dir.lower() != "none" else None

operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
assert operator_out_dir is not None


# File-extension to search for in the input-dir
input_file_extension = "*.dcm"

# How many processes should be started?
parallel_processes = 3
exit_on_issue = True

logger.info("##################################################")
logger.info("#")
logger.info("# Starting Mask2Nifti Operator:")
logger.info("#")
logger.info(f"# workflow_dir:      {workflow_dir}")
logger.info(f"# batch_name:        {batch_name}")
logger.info(f"# seg_filter:        {seg_filter}")
logger.info(f"# exit_on_issue:     {exit_on_issue}")
logger.info(f"# operator_in_dir:   {operator_in_dir}")
logger.info(f"# base_dicom_in_dir: {base_dicom_in_dir}")
logger.info(f"# operator_out_dir:  {operator_out_dir}")
logger.info(f"# parallel_processes:{parallel_processes}")
logger.info("#")
logger.info("##################################################")
logger.info("#")
logger.info("# Starting processing on BATCH-ELEMENT-level ...")
logger.info("#")
logger.info("##################################################")
logger.info("#")

todo_list = []
batch_folders = sorted([f for f in glob(join("/", workflow_dir, batch_name, "*"))])
for batch_element_dir in batch_folders:
    logger.info("#")
    logger.info(f"# Processing batch-element {batch_element_dir}")
    logger.info("#")
    element_mask_dicom_dir = join(batch_element_dir, operator_in_dir)
    element_output_dir = join(batch_element_dir, operator_out_dir)

    if not exists(element_mask_dicom_dir):
        logger.error("#")
        logger.error(
            f"# element_mask_dicom_dir: {element_mask_dicom_dir} does not exists!"
        )
        logger.error("#")
        exit(1)

    if base_dicom_in_dir is not None:
        element_base_dicom_in_dir = join(batch_element_dir, base_dicom_in_dir)
        if not exists(element_base_dicom_in_dir):
            logger.error("#")
            logger.error(
                f"# element_base_dicom_in_dir: {element_base_dicom_in_dir} does not exists!"
            )
            logger.error("#")
            exit(1)
    else:
        element_base_dicom_in_dir = None

    # creating output dir
    Path(element_output_dir).mkdir(parents=True, exist_ok=True)

    # creating output dir
    element_mask_dicoms = glob(
        join(element_mask_dicom_dir, input_file_extension), recursive=False
    )
    logger.info(f"# Found {len(element_mask_dicoms)} mask-dcm-files!")

    # Single process:
    # Loop for every input-file found with extension 'input_file_extension'
    for element_mask_dicom in element_mask_dicoms:
        todo_list.append(
            (
                element_mask_dicom,
                element_base_dicom_in_dir,
                element_output_dir,
                seg_filter,
            )
        )

logger.info(f"# Got {len(todo_list)} jobs in the todo-list!")
with ThreadPool(parallel_processes) as threadpool:
    results = threadpool.imap_unordered(process_input_file, todo_list)

    for success, input_file in results:
        if not success and exit_on_issue:
            logger.error("# An issue occurred! -> exit")
            exit(1)

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
    batch_output_dir = join("/", workflow_dir, operator_out_dir)
    batch_base_dicom_in_dir = join("/", workflow_dir, base_dicom_in_dir)

    # check if input dir present
    if not exists(batch_input_dir):
        logger.warning("#")
        logger.warning(f"# Input-dir: {batch_input_dir} does not exists!")
        logger.warning("# -> skipping")
        logger.warning("#")
    else:
        # creating output dir
        Path(batch_output_dir).mkdir(parents=True, exist_ok=True)

        # creating output dir
        batch_mask_dicoms = glob(
            join(batch_input_dir, input_file_extension), recursive=False
        )
        logger.info(f"# Found {len(batch_mask_dicoms)} batch_mask_dicoms-files!")

        for batch_mask_dicom in batch_mask_dicoms:
            success, input_file = process_input_file(
                (
                    batch_mask_dicom,
                    batch_base_dicom_in_dir,
                    batch_output_dir,
                    seg_filter,
                )
            )
            if not success and exit_on_issue:
                logger.error("# An issue occurred! -> exit")
                exit(1)

    logger.info("#")
    logger.info("##################################################")
    logger.info("#")
    logger.info("# BATCH-LEVEL-level processing done.")
    logger.info("#")
    logger.info("##################################################")
    logger.info("#")

if processed_count == 0:
    logger.error("#")
    logger.error("##################################################")
    logger.error("#")
    logger.error("##################  ERROR  #######################")
    logger.error("#")
    logger.error("# ----> NO FILES HAVE BEEN PROCESSED!")
    logger.error("#")
    logger.error("##################################################")
    logger.error("#")
    exit(1)
else:
    logger.info("#")
    logger.info(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
    logger.info("#")
    logger.info("# DONE #")
