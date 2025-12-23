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
from os.path import join, basename, exists, splitext
from glob import glob
from typing import Dict, List, Any, Optional
from collections import defaultdict
import SimpleITK as sitk
import numpy as np
from matplotlib import colormaps

import segmentation_defaults
from kaapanapy.logger import get_logger

# Logger
logger = get_logger(__name__, logging.INFO)


# base color map
cmap = colormaps.get_cmap("gist_ncar")

# --- Mapping model to its outputs ---
# See here: https://github.com/UMEssen/Body-and-Organ-Analysis/blob/main/documentation/pacs_integration.md#Outputs
model_outputs = {
    "body": [
        "body_extremities",
        "body_trunc",
    ],  # Nowhere defined so only assumed from testing
    "total": ["total"],
    "lung_vessels": ["lung_vessels_airways"],
    "cerebral_bleed": ["cerebral_bleed"],
    "hip_implant": ["hip_implant"],
    "coronary_arteries": ["coronary_arteries"],
    "pleural_pericard_effusion": ["pleural_pericard_effusion"],
    "liver_vessels": ["liver_vessels"],
    "bca": ["body-parts", "body-regions", "tissues"],
}


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


def get_needed_outputs() -> List[str]:
    """
    Determines which segmentation outputs are required based on selected models
    defined in environment variables. If STRICT_MODE is not enabled, returns empty.

    Returns:
        list[str]: List of required segmentation output basenames.
    """
    strict_mode = (
        True if environ.get("STRICT_MODE", "false").lower() == "true" else False
    )

    # Guard clause: Only continue if strict mode is on and model_outputs is set
    if not (strict_mode and model_outputs):
        return []
    logger.debug(environ["MODELS"])
    selected_models = [
        model.strip("'\"\\,") for model in environ.get("MODELS", []).strip("[]").split()
    ]
    if "total" in selected_models:
        logger.debug(environ["TOTAL_MODELS"])
        selected_models.extend(
            [
                model.strip("'\"\\,")
                for model in environ.get("TOTAL_MODELS", []).strip("[]").split()
            ]
        )

    needed_output_names = []
    logger.debug(selected_models)
    for model in selected_models:
        logger.debug(model)
        needed_output_names.extend(model_outputs[model])
    return needed_output_names


def strip_all_extensions(filename):
    """
    Strips all file extensions from a filename (including double extensions like .nii.gz).

    Args:
        filename (str): The input filename.

    Returns:
        str: The filename without extensions.
    """
    while True:
        filename, ext = splitext(filename)
        if ext == "":
            break
    return filename


def generate_series_description() -> str:
    """
    Generates a description string for the series based on the selected models
    and DAG_ID environment variable. The function sanitizes the model names
    from the 'MODELS' and 'TOTAL_MODELS' environment variables to ensure they
    are formatted correctly without extra characters like quotes.

    Returns:
        str: A formatted string containing the DAG ID and the models in use.
    """
    # Retrieve and sanitize the selected models from the "MODELS" environment variable
    selected_models = [
        model.strip("'\"\\,") for model in environ.get("MODELS", []).strip("[]").split()
    ]

    # If "total" is included in the selected models, add models from the "TOTAL_MODELS" environment variable
    if "total" in selected_models:
        selected_models.extend(
            [
                model.strip("'\"\\,")
                for model in environ.get("TOTAL_MODELS", []).strip("[]").split()
            ]
        )

    # Join the selected models into a comma-separated string for the description
    models_str = ", ".join(selected_models)

    # Return the formatted description string
    return f'{environ["DAG_ID"]} - Models: {models_str}'


if __name__ == "__main__":
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

        # Validate required segmentations if STRICT_MODE is enabled
        needed_segmentations = get_needed_outputs()
        if needed_segmentations:
            available_basenames = {
                strip_all_extensions(basename(f)) for f in segmentation_files
            }

            # Find missing segmentations
            missing = [n for n in needed_segmentations if n not in available_basenames]
            if missing:
                output_to_model = {}
                for model, outputs in model_outputs.items():
                    for output in outputs:
                        output_to_model.setdefault(output, []).append(model)
                logger.error("The following required segmentation outputs are missing:")
                for m in missing:
                    models = output_to_model.get(m, ["<unknown model>"])
                    logger.error(
                        f"  - {m} (required for model(s): {', '.join(models)})"
                    )
                exit(1)
            # Find additional segmentations
            additional = [
                n for n in available_basenames if n not in needed_segmentations
            ]
            if additional:
                logger.info(
                    "The following additional segmentation outputs are present but not required:"
                )
                for a in additional:
                    logger.info(f"  - {a}")

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
        output_dir = join("/", workflow_dir, batch_dir, series_uid, operator_out_dir)
        label_entries_collection = []
        for idx, file_path in enumerate(segmentation_files):
            image_basename = basename(file_path)
            rootname = strip_all_extensions(image_basename)

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

            label_entries_collection.append(label_entries)

        # Update how many batches this file has appeared in (and was valid, i.e. not background-only)
        for filename in seen_in_this_batch:
            file_occurrences[filename] += 1

        # Save empty seg_info.json as placeholder/dummy
        empty_seg_info = {"seg_info": label_entries_collection}

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
