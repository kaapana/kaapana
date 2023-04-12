import os
from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
from totalsegmentator.python_api import totalsegmentator
from logger_helper import get_logger
import logging
import torch
import json


# Process each file
def process_input_file(input_path, output_path_nii):
    global processed_count, task, output_type, multilabel, fast, preview, statistics, radiomics, body_seg, force_split, quiet, verbose, nr_thr_resamp, nr_thr_saving, roi_subset
    logger.info(f"{basename(input_file)}: start processing ...")

    try:
        totalsegmentator(
            input=Path(input_path).absolute(),
            output=Path(output_path_nii).absolute(),
            ml=multilabel,
            nr_thr_resamp=nr_thr_resamp,
            nr_thr_saving=nr_thr_saving,
            fast=fast,
            nora_tag=nora_tag,
            preview=preview,
            task=task,
            roi_subset=roi_subset,
            statistics=statistics,
            radiomics=radiomics,
            crop_path=None,
            body_seg=body_seg,
            force_split=force_split,
            output_type=output_type,
            quiet=quiet,
            verbose=verbose,
            test=0,
        )
        processed_count += 1

        logger.info(f"{basename(input_file)}: finished successully!")
        return True, input_path

    except Exception as e:
        logger.error(f"{basename(input_file)}: something went wrong.!")
        logger.error(e)
        return False, input_path


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
    processed_count = 0
    issue_occurred = False

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

    enable_lung_vessels = getenv("LUNG_VESSELS", "False")
    enable_lung_vessels = True if enable_lung_vessels.lower() == "true" else False

    enable_cerebral_bleed = getenv("CEREBRAL_BLEED", "False")
    enable_cerebral_bleed = True if enable_cerebral_bleed.lower() == "true" else False

    enable_hip_implant = getenv("HIP_IMPLANT", "False")
    enable_hip_implant = True if enable_hip_implant.lower() == "true" else False

    enable_coronary_arteries = getenv("CORONARY_ARTERIES", "False")
    enable_coronary_arteries = (
        True if enable_coronary_arteries.lower() == "true" else False
    )

    enable_body = getenv("BODY", "False")
    enable_body = True if enable_body.lower() == "true" else False

    enable_pleural_pericard_effusion = getenv("PLEURAL_PERICARD_EFFUSION", "False")
    enable_pleural_pericard_effusion = (
        True if enable_pleural_pericard_effusion.lower() == "true" else False
    )

    task = getenv("TASK", "None")
    task = task if task.lower() != "none" else None

    # output_type: choices=["nifti", "dicom"] "Select if segmentations shall be saved as Nifti or as Dicom RT Struct image."
    output_type = getenv("OUTPUT_TYPE", "None")
    output_type = output_type if output_type.lower() != "none" else None

    # "Save one multilabel image for all classes"
    multilabel = getenv("MULTILABEL", "False").lower() in ("true", "1", "t")

    # Run faster lower resolution model
    fast = getenv("FAST", "False").lower() in ("true", "1", "t")
    # Generate a png preview of segmentation default=False
    preview = getenv("PREVIEW", "False").lower() in ("true", "1", "t")
    # Calc volume (in mm3) and mean intensity. Results will be in statistics.json
    statistics = getenv("STATISTICS", "False").lower() in ("true", "1", "t")
    # Calc radiomics features. Requires pyradiomics. Results will be in statistics_radiomics.json
    radiomics = getenv("RADIOMICS", "False").lower() in ("true", "1", "t")
    # Do initial rough body segmentation and crop image to body region
    body_seg = getenv("BODYSEG", "False").lower() in ("true", "1", "t")
    # Process image in 3 chunks for less memory consumption
    force_split = getenv("FORCESPLIT", "False").lower() in ("true", "1", "t")
    # Print no intermediate outputs
    quiet = getenv("QUIET", "False").lower() in ("true", "1", "t")
    # Show more intermediate output
    verbose = getenv("VERBOSE", "False").lower() in ("true", "1", "t")

    # Nr of threads for resampling default=1
    nr_thr_resamp = getenv("NR_THR_RESAMP", "None")
    nr_thr_resamp = nr_thr_resamp if nr_thr_resamp.lower() != "none" else None
    assert nr_thr_resamp != None
    nr_thr_resamp = int(nr_thr_resamp)
    # Nr of threads for saving segmentations default=6
    nr_thr_saving = getenv("NR_THR_SAVING", "None")
    nr_thr_saving = nr_thr_saving if nr_thr_saving.lower() != "none" else None
    assert nr_thr_saving != None
    nr_thr_saving = int(nr_thr_saving)

    # tag in nora as mask. Pass nora project id as argument. default="None
    nora_tag = getenv("NORA_TAG", "None")
    nora_tag = nora_tag if nora_tag.lower() != "none" else None

    # Define a subset of classes to save (space separated list of class names). If running 1.5mm model, will only run the appropriate models for these rois.")
    roi_subset = getenv("ROI_SUBSET", "None")
    roi_subset = roi_subset if roi_subset.lower() != "none" else None

    cuda_available = getenv("CUDA_VISIBLE_DEVICES", "None")
    cuda_available = True if cuda_available.lower() != "none" else False

    os.environ["TOTALSEG_WEIGHTS_PATH"] = str("/models/total_segmentator")

    # if not cuda_available or not torch.cuda.is_available():
    if not torch.cuda.is_available():
        logger.warning("")
        logger.warning(
            "###############################################################################"
        )
        logger.warning(
            "#                                                                             #"
        )
        logger.warning(
            "#      CUDA is not available! -> switching to CPU and enforce --fast !!       #"
        )
        logger.warning(
            "#                                                                             #"
        )
        logger.warning(
            "###############################################################################"
        )
        logger.warning("")
        fast = True

    tasks_available = [
        "total",
        "lung_vessels",
        "cerebral_bleed",
        "hip_implant",
        "coronary_arteries",
        "body",
        "pleural_pericard_effusion",
        "liver_vessels",
        "bones_extremities",
        "tissue_types",
        "heartchambers_highres",
        "head",
        "aortic_branches",
        "heartchambers_test",
        "bones_tissue_test",
        "aortic_branches_test",
        "test",
    ]
    assert task in tasks_available

    if task == "lung_vessels" and not enable_lung_vessels:
        logger.warning(f"# task: {task} disabled -> skipping")
        exit(0)
    elif task == "cerebral_bleed" and not enable_cerebral_bleed:
        logger.warning(f"# task: {task} disabled -> skipping")
        exit(0)
    elif task == "hip_implant" and not enable_hip_implant:
        logger.warning(f"# task: {task} disabled -> skipping")
        exit(0)
    elif task == "coronary_arteries" and not enable_coronary_arteries:
        logger.warning(f"# task: {task} disabled -> skipping")
        exit(0)
    elif task == "body" and not enable_body:
        logger.warning(f"# task: {task} disabled -> skipping")
        exit(0)
    elif task == "pleural_pericard_effusion" and not enable_pleural_pericard_effusion:
        logger.warning(f"# task: {task} disabled -> skipping")
        exit(0)

    json_path = "/kaapana/app/seg_info_lookup.json"
    with open(json_path, encoding="utf-8") as seg_info_lookup:
        seg_info_lookup_dict = json.load(seg_info_lookup)

    assert task in seg_info_lookup_dict
    seg_info_dict = seg_info_lookup_dict[task]

    # File-extension to search for in the input-dir
    input_file_extension = "*.nii.gz"

    logger.info("##################################################")
    logger.info("#")
    logger.info("# Starting TotalSegmentator:")
    logger.info("#")
    logger.info(f"# workflow_dir:     {workflow_dir}")
    logger.info(f"# batch_name:       {batch_name}")
    logger.info(f"# operator_in_dir:  {operator_in_dir}")
    logger.info(f"# operator_out_dir: {operator_out_dir}")
    logger.info("#")
    logger.info("#")
    logger.info("# Config:")
    logger.info("#")
    logger.info(f"# {task=}")
    logger.info(f"# {output_type=}")
    logger.info(f"# {multilabel=}")
    logger.info(f"# {fast=}")
    logger.info(f"# {preview=}")
    logger.info(f"# {statistics=}")
    logger.info(f"# {radiomics=}")
    logger.info(f"# {body_seg=}")
    logger.info(f"# {force_split=}")
    logger.info(f"# {quiet=}")
    logger.info(f"# {verbose=}")
    logger.info(f"# {roi_subset =}")
    logger.info(f"# {nr_thr_resamp=}")
    logger.info(f"# {nr_thr_saving=}")
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

        # creating output dir
        output_path_nii = join(element_output_dir, "segmentations")
        Path(output_path_nii).mkdir(parents=True, exist_ok=True)
        seg_info_path = join(element_output_dir, f"{task}_seg_info.json")
        with open(seg_info_path, "w") as fp:
            json.dump(seg_info_dict, fp, indent=4)

        # creating output dir
        input_files = glob(
            join(element_input_dir, input_file_extension), recursive=True
        )
        logger.info(f"# Found {len(input_files)} input-files -> start processing ...")

        for input_file in input_files:
            success, input_file = process_input_file(
                input_path=input_file, output_path_nii=output_path_nii
            )
            if not success:
                issue_occurred = True

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
            output_path_nii = join(batch_output_dir, "segmentations")

            Path(output_path_nii).mkdir(parents=True, exist_ok=True)
            seg_info_path = join(output_path_nii, "seg_info.json")
            if exists(seg_info_path):
                with open(seg_info_path, "r") as f:
                    existing_seg_info_dict = json.load(f)
                    seg_info_dict.update(existing_seg_info_dict)

            with open(seg_info_path, "w") as fp:
                json.dump(seg_info_dict, fp, indent=4)

            # creating output dir
            input_files = glob(
                join(batch_input_dir, input_file_extension), recursive=True
            )
            logger.info(f"# Found {len(input_files)} input-files!")

            # Single process:
            # Loop for every input-file found with extension 'input_file_extension'
            for input_file in input_files:
                success, input_file = process_input_file(
                    input_path=input_file, output_path_nii=output_path_nii
                )
                if not success:
                    issue_occurred = True

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
