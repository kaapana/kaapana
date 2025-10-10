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
from typing import Dict, List, Any, Optional
from collections import defaultdict
import SimpleITK as sitk
import numpy as np
from matplotlib import cm

import segmentation_defaults
from metadata_generator import (
    build_segmentation_information,
    map_labels_to_segment_attributes,
)

# base color map
cmap = cm.get_cmap("gist_ncar")


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

    file_occurrences = defaultdict(int)  # Tracks how many batches each file appears in
    all_batches = 0
    existing_files = []
    problem_files = defaultdict(
        list
    )  # Stores filenames with list of reasons they are problematic

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
        all_batches += 1
        seen_in_this_batch = set()

        series_uid = basename(input_dir)

        # Step 1: Find segmentation files in the input directory
        segmentation_files = []
        for ext in ("*.nii", "*.nii.gz", "*.nrrd"):
            segmentation_files.extend(glob(join(input_dir, ext)))
        segmentation_files.sort(key=str.lower)

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
        segment_attributes = []
        output_dir = join("/", workflow_dir, batch_dir, series_uid, operator_out_dir)
        # For Colormmap
        num_files = len(segmentation_files)
        for idx, file_path in enumerate(segmentation_files):
            image_basename = basename(file_path)
            rootname = image_basename.split(".")[0]

            # Image-specific output directory
            image_output_dir = output_dir

            if not exists(image_output_dir):
                try:
                    makedirs(image_output_dir)
                    logger.info(f"Created output directory: {image_output_dir}")
                except Exception as e:
                    logger.error(
                        f"Could not create output directory '{image_output_dir}': {e}"
                    )
                    continue

            # Extract declared label info from measurement metadata or fallback enum
            label_entries = extract_labels(measurement_info, rootname, logger)
            declared_ids = set(entry["label_int"] for entry in label_entries)

            # Read image data to find unique label IDs (excluding background = 0)
            try:
                image = sitk.ReadImage(file_path)
                array = sitk.GetArrayFromImage(image)
                unique_vals = np.unique(array)
                image_label_ids = set(int(v) for v in unique_vals if v != 0)
            except Exception as e:
                logger.error(f"Failed to read image '{file_path}': {e}")
                continue

            if image_label_ids:
                seen_in_this_batch.add(image_basename)
            else:
                # File contains only background; mark as problematic for this batch
                logger.warning(
                    f"Skipping file '{image_basename}' in {series_uid} — contains only background (label 0)"
                )
                problem_files[image_basename].append("only background")
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

            # Add fallback labels for any labels found in image but missing from declared metadata
            missing_ids = image_label_ids - declared_ids
            for i, mid in enumerate(sorted(missing_ids), start=1):
                fallback_name = f"unnamed_{rootname}_{i}"
                label_entries.append({"label_int": mid, "label_name": fallback_name})

            segment_attributes.append(
                map_labels_to_segment_attributes(label_entries=label_entries)
            )

        # Update how many batches this file has appeared in (and was valid, i.e. not background-only)
        for filename in seen_in_this_batch:
            file_occurrences[filename] += 1
        # assign the colors for the segments equidistant
        all_segments = [
            segment for sublist in segment_attributes for segment in sublist
        ]
        num_segments = len(all_segments)
        if num_segments == 0:
            logger.warning("No segments found to assign colors.")
        else:
            # Generate equidistant color partitions between 0 and 1 for each segment
            color_positions = np.linspace(0, 1, num_segments)

            for i, segment in enumerate(all_segments):
                color = (
                    np.round(np.array(cmap(color_positions[i])[:3]) * 255)
                    .astype(int)
                    .tolist()
                )
                segment["recommendedDisplayRGBValue"] = color
        # write the MetaInfo.json for this batch
        metainfo_filename = join(output_dir, "body-and-organ-analysis.json")
        with open(metainfo_filename, "w") as f:
            json.dump(
                build_segmentation_information(
                    segment_attributes=segment_attributes,
                    series_description="body-and-organ-analysis",
                ),
                f,
                indent=4,
            )

        # Empty seg_info.json
        empty_seg_info = {"seg_info": []}

        with open(join(output_dir, "seg_info.json"), "w") as f:
            json.dump(empty_seg_info, f, indent=4)

    # Step 4: After processing all batches, determine which files are complete or problematic
    for filename, count in file_occurrences.items():
        if count == all_batches:
            existing_files.append(filename)
        else:
            missing_in = all_batches - count
            # Mark file as missing in some batches, adding reason with counts
            problem_files[filename].append(
                f"missing in {missing_in} of {all_batches} batches"
            )

    logger.info("Files summary:")
    logger.info("Existing Files: %s", existing_files)
    logger.info("Problem Files: %s", dict(problem_files))

    logger.info("All image label info exported.")
