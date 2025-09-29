"""
This script processes medical image segmentations by extracting label information
and exporting label metadata for each segmentation image. It assumes a specific
directory structure based on environmental variables and uses the SimpleITK and
NumPy libraries for DICOM-compatible image handling.

Steps performed:
1. Search for segmentation files (.nii, .nii.gz, .nrrd) in a given input directory.
2. Load optional measurement metadata from a `total-measurements.json` file.
3. Extract label information, either from metadata or from a fallback enum class.
4. Copy the segmentation file to a new output directory.
5. Save a corresponding JSON file with label information per image.
"""

import logging
import json
import shutil
from os import environ, makedirs
from os.path import join, basename, exists
from glob import glob
from typing import Dict, List, Set, Any, Optional
import SimpleITK as sitk
import numpy as np
import segmentation_defaults


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Creates and configures a logger with the specified name and logging level.

    Args:
        name (str): Name of the logger.
        level (int): Logging level (e.g., logging.INFO, logging.DEBUG).

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logger.hasHandlers():
        logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def hyphen_to_camel_case(s: str) -> str:
    """
    Converts a hyphen- or underscore-separated string to CamelCase.

    Args:
        s (str): The input string (e.g., 'head-neck').

    Returns:
        str: The CamelCase version of the string (e.g., 'HeadNeck').
    """
    import re

    parts = re.split("[-_]", s)
    return "".join(part.capitalize() for part in parts)


def extract_labels(
    measurement_info: Optional[Dict[str, Any]], rootname: str, logger: logging.Logger
) -> List[Dict[str, Any]]:
    """
    Extracts label entries for a segmentation image either from provided measurement
    metadata or by falling back to an enum in segmentation_defaults.

    Args:
        measurement_info (dict): The measurement metadata loaded from JSON.
        rootname (str): The root name of the image (used to look up labels).
        logger (logging.Logger): Logger instance for logging messages.

    Returns:
        list[dict]: A list of dictionaries containing label_int and label_name.
    """
    segmentations = measurement_info.get("segmentations") if measurement_info else None
    group = segmentations.get(rootname) if segmentations else None

    if group:
        logger.info(f"Extracted {len(group)} declared label(s) for '{rootname}'")
        return [
            {"label_int": idx + 1, "label_name": label}
            for idx, label in enumerate(group.keys())
        ]

    enum_cls = getattr(segmentation_defaults, hyphen_to_camel_case(rootname), None)
    if enum_cls:
        return [
            {"label_int": member.value, "label_name": member.name.lower()}
            for member in enum_cls
        ]

    logger.warning(f"No declared labels or enums found for '{rootname}'")
    return []


if __name__ == "__main__":
    logger = get_logger(__name__, logging.INFO)

    # Environment-based paths
    workflow_dir = environ["WORKFLOW_DIR"]
    operator_in_dir = environ["OPERATOR_IN_DIR"]
    operator_out_dir = environ["OPERATOR_OUT_DIR"]
    batch_dir = environ["BATCH_NAME"]

    # Path where all series UID folders are found
    series_root = join("/", workflow_dir, operator_in_dir)
    series_uid_folders = sorted(glob(join(series_root, "*")))
    logger.info(f"Found {len(series_uid_folders)} series UID folder(s)")

    for input_dir in series_uid_folders:
        series_uid = basename(input_dir)

        # Step 1: Find segmentation files in the input directory
        segmentation_files = []
        for ext in ("*.nii", "*.nii.gz", "*.nrrd"):
            segmentation_files.extend(glob(join(input_dir, ext)))

        logger.info(
            f"Found {len(segmentation_files)} segmentation file(s) in {series_uid}"
        )

        # Step 2: Load measurement info ONCE per series
        measurement_info_file = join(input_dir, "total-measurements.json")
        measurement_info = {}
        if exists(measurement_info_file):
            with open(measurement_info_file, "r") as f:
                try:
                    measurement_info = json.load(f)
                    logger.info(f"Loaded measurement info for {series_uid}")
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Could not parse measurement info for {series_uid}: {e}"
                    )
        else:
            logger.warning(f"No measurement info found for {series_uid}")

        # Step 3: Process each segmentation image
        for file_path in segmentation_files:
            image_basename = basename(file_path)
            rootname = image_basename.split(".")[0]

            # Image-specific output directory
            image_output_dir = join(
                "/", workflow_dir, batch_dir, series_uid, operator_out_dir, rootname
            )

            if not exists(image_output_dir):
                try:
                    makedirs(image_output_dir)
                    logger.info(f"Created output directory: {image_output_dir}")
                except Exception as e:
                    logger.error(
                        f"Could not create output directory '{image_output_dir}': {e}"
                    )
                    continue

            # Copy image to image_output_dir
            dest_path = join(image_output_dir, image_basename)
            if not exists(dest_path):
                try:
                    shutil.copy2(file_path, dest_path)
                    logger.info(f"Copied: {image_basename} -> {image_output_dir}")
                except Exception as e:
                    logger.error(f"Failed to copy file '{file_path}' to output: {e}")
                    continue

            # Extract declared labels
            label_entries = extract_labels(measurement_info, rootname, logger)
            declared_ids = set(entry["label_int"] for entry in label_entries)

            # Read image to extract label IDs
            try:
                image = sitk.ReadImage(file_path)
                array = sitk.GetArrayFromImage(image)
                unique_vals = np.unique(array)
                image_label_ids = set(int(v) for v in unique_vals if v != 0)
            except Exception as e:
                logger.error(f"Failed to read image '{file_path}': {e}")
                continue

            # Add fallback labels if needed
            missing_ids = image_label_ids - declared_ids
            for i, mid in enumerate(sorted(missing_ids), start=1):
                fallback_name = f"unnamed_{rootname}_{i}"
                label_entries.append({"label_int": mid, "label_name": fallback_name})

            # Write <image>_seg_info.json
            out_path = join(image_output_dir, f"{rootname}_seg_info.json")
            try:
                with open(out_path, "w") as f:
                    json.dump({"seg_info": label_entries}, f, indent=4)
                logger.info(f"Saved seg info: {out_path}")
            except Exception as e:
                logger.error(f"Failed to write seg info file '{out_path}': {e}")

    logger.info("All image label info exported.")
