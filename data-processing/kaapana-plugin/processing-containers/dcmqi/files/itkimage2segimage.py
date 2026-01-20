"""
Convert ITK segmentation volumes to DICOM SEG (dcmqi itkimage2segimage)
======================================================================

This script converts segmentation volumes (e.g. nnU-Net outputs) into DICOM SEG
objects using dcmqi's `itkimage2segimage` binary.

It is workflow-engine agnostic: it relies only on environment variables and a
batch directory layout. It can therefore be executed from Airflow/Kaapana, other
workflow engines, or directly from the command line.

Directory layout
----------------
The script processes "batch element" folders located at:

  /<WORKFLOW_DIR>/<BATCH_NAME>/*

Within each batch element directory:

- Input DICOM directory:
    <batch_element_dir>/<OPERATOR_IN_DIR>
  Used as the reference image series for dcmqi and for extracting:
    - Clinical Trial Protocol ID (0012,0020) -> stored as `aetitle` identifier
    - Body Part Examined (0018,0015)         -> fallback body part if none provided

- Segmentation directory:
    <batch_element_dir>/<OPERATOR_IMAGE_LIST_INPUT_DIR>
  Contains segmentation volumes to convert (see supported formats below).

- Output directory:
    <batch_element_dir>/<OPERATOR_OUT_DIR>
  Will be created if missing and will contain produced DICOM SEG files.

Supported segmentation file extensions
-------------------------------------
- .nrrd
- .nii
- .nii.gz

Outputs
-------
Metadata JSON files are written into the segmentation directory
(OPERATOR_IMAGE_LIST_INPUT_DIR). DICOM SEG objects are written into the output
directory (OPERATOR_OUT_DIR).

Depending on configuration, this script may produce:

- Single-label DICOM SEG files:
    One SEG output per input segmentation file (INPUT_TYPE="single_label_segs").

- A combined DICOM SEG file:
    Exactly one combined SEG output per batch element, built from either:
      - one or multiple segmentation volumes in multi-label mode
        (INPUT_TYPE="multi_label_seg"), or
      - multiple single-label segmentations when
        CREATE_MULTI_LABEL_DCM_FROM_SINGLE_LABEL_SEGS=true.

Output filenames are derived from the segmentation filename "rootname":
- "<rootname>.json" (metadata) in OPERATOR_IMAGE_LIST_INPUT_DIR
- "<rootname>.dcm"  (DICOM SEG) in OPERATOR_OUT_DIR

IMPORTANT: rootname collisions
------------------------------
Rootnames are computed from the file name without its segmentation extension
(case-insensitive). If multiple segmentation files map to the same rootname,
their outputs would overwrite each other (both .json and .dcm). The script checks
this early and fails with a detailed collision report.

Configuration (Environment Variables)
-------------------------------------
Required (directory layout / workflow glue):
- WORKFLOW_DIR
- BATCH_NAME
- OPERATOR_IN_DIR
- OPERATOR_IMAGE_LIST_INPUT_DIR
- OPERATOR_OUT_DIR

General:
- INPUT_TYPE: "single_label_segs" or "multi_label_seg"
- DCMQI_BIN_DIR: path to dcmqi binaries (default: /kaapana/app/dcmqi/bin)
- SERIES_DISCRIPTION: base SeriesDescription (note: env var name contains a typo)
- SERIES_NUMBER: default "300"
- INSTANCE_NUMBER: default "1"
- CREATOR_NAME: ContentCreatorName (default: "kaapana")
- ALGORITHM_NAME: SegmentAlgorithmName (default: "kaapana")
- ALGORITHM_TYPE: SegmentAlgorithmType (default: "AUTOMATIC")

Behavior flags:
- SKIP_EMPTY_SLICES:
    If true, call dcmqi with "--skip" (may affect MITK usability).
- FAIL_ON_NO_SEGMENTATION_FOUND:
    If true, fail a batch element when no segmentation files are found.
- REUSE_EXISTING_METADATA:
    If true, keep existing .json metadata files if present.

Single-label mode (INPUT_TYPE="single_label_segs"):
- SINGLE_LABEL_SEG_INFO:
    - "from_file_name" -> derive label name from file rootname
    - otherwise        -> use provided value as label name for ALL segmentations
                          in the batch element
- CREATE_MULTI_LABEL_DCM_FROM_SINGLE_LABEL_SEGS:
    - if true, also produce one combined multi-label SEG in addition to the
      per-file outputs

Multi-label mode (INPUT_TYPE="multi_label_seg"):
- MULTI_LABEL_SEG_INFO_JSON:
    Name of the job JSON file in OPERATOR_IMAGE_LIST_INPUT_DIR
    (default: "seg_info.json")
- MULTI_LABEL_SEG_NAME:
    Output name used for the combined SEG object (default: "multi-label")

Multi-label job JSON format (seg_info)
--------------------------------------
In INPUT_TYPE="multi_label_seg", a JSON file in OPERATOR_IMAGE_LIST_INPUT_DIR must
exist and contain the key "seg_info":

  {"seg_info": ...}

The "seg_info" value is flexible and is normalized by
`metadata_helper.normalize_seg_info` into the dcmqi schema structure
(list-of-lists of dicts).

Accepted "seg_info" shapes:

1) list[str]
   {"seg_info": ["spleen", "right@kidney"]}

2) list[list[str]]  (multiple groups)
   {"seg_info": [["liver", "spleen"], ["right@kidney", "left@kidney"]]}

3) dict (single label object)
   {"seg_info": {"label_name": "spleen", "label_int": 1}}

4) list[dict]
   {"seg_info": [{"label_name": "spleen"}, {"label_name": "right@kidney"}]}

5) list[list[dict]]  (multiple groups with explicit IDs)
   {"seg_info": [[{"label_name": "liver", "label_int": 1},
                  {"label_name": "spleen", "label_int": 2}]]}

Important: group consistency
----------------------------
Each group must be internally consistent:
- A group must be either a list of strings OR a list of dicts (do not mix).
- For dict-based groups, label_int is all-or-none within the group:
    either every label dict provides label_int, or none do (then IDs are generated 1..N).

Mapping seg_info groups to segmentation volumes
-----------------------------------------------
In multi-label mode, segmentation volumes in OPERATOR_IMAGE_LIST_INPUT_DIR are
sorted case-insensitively before processing.

- If exactly one segmentation file is present, "seg_info" must define exactly one
  group (i.e. list[str], list[dict], or a single dict).

- If multiple segmentation files are present, "seg_info" must be list[list[...]]
  with one group per file, and the group order must match the sorted file order.

Label ID ("label_int") rules:
  - If label_int is omitted, IDs are generated starting at 1 within each group.
  - If label_int is provided, it is preserved and may be non-consecutive and
    sparse (e.g. 1, 5, 42). This supports segmentations with non-standard label
    numbering.
  - label_int == 0 is reserved for background only and is allowed only when
    label_name matches "background" or "__background__" (case-insensitive).
  - label_int < 0 is invalid.
  - Within a group, entries must be uniform: all strings or all dicts (no mixing).

Optional multi-label job JSON keys:
- "task_body_part": string
    Overrides the Body Part Examined written into the combined SEG (0018,0015).
- "algorithm": string
    Adds an algorithm tag to the SeriesDescription used for the combined SEG:
      - if SERIES_DISCRIPTION is set: "<series_description> | algorithm=<ALGORITHM_NAME>-<algorithm>"
      - otherwise: "<ALGORITHM_NAME>-<algorithm>"

DICOM tags written into output SEG
----------------------------------
After dcmqi creates the SEG, the script post-processes the output to set:

- Body Part Examined (0018,0015):
    - if task_body_part is provided (multi-label JSON), use it
    - else if input DICOM series contains (0018,0015), reuse it
    - else leave unchanged

- Clinical Trial Protocol ID (0012,0020):
    - reused from the first input DICOM file if present, otherwise "internal"

Coding scheme behavior (metadata_helper)
----------------------------------------
Segment attributes are built using metadata_helper.create_segment_attribute():
- attempts to resolve coding information from code_lookup_table.json
- matches tags case-insensitively using exact/partial/word-level matching
- falls back to a "Custom" placeholder coding scheme if nothing matches

Logging and counters
--------------------
The final summary reports the number of created DICOM SEG outputs (".dcm") across
all processed batch elements. It is not a count of input segmentation volumes.

References
----------
- dcmqi SEG metadata example schema:
  https://github.com/QIICR/dcmqi/blob/master/doc/examples/seg-example.json
- dcmqi documentation:
  https://qiicr.gitbook.io/dcmqi-guide/
- DICOM Part 16, Context Groups (Chapter L):
  http://dicom.nema.org/medical/dicom/current/output/chtml/part16/chapter_L.html#chapter_L
- DICOM tag references (convenient browser):
  https://dicom.innolitics.com/
"""

import os
import json
import glob
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping, Optional, Sequence, cast

import numpy as np
import pydicom
from matplotlib import cm

import logging
from kaapanapy.logger import get_logger

from metadata_helper import (
    create_segment_attribute,
    process_seg_info,
    normalize_seg_info,
)

# Logger
logger = get_logger(__name__, logging.INFO)

# Supported segmentation file extensions (case-insensitive).
# Used for validating inputs and deriving "rootname" (output base name).
_ALLOWED_SUFFIXES = (".nii.gz", ".nii", ".nrrd")

# Default location of the dcmqi binaries. Can be overridden via DCMQI_BIN_DIR.
_DCMQI_DEFAULT_BIN_DIR = "/kaapana/app/dcmqi/bin"


# -----------------------------
# Helpers
# -----------------------------
def env_bool(name: str, default: bool = False) -> bool:
    """
    Read an environment variable as a boolean flag.

    Parameters
    ----------
    name:
        Environment variable name.
    default:
        Value used when the variable is unset.

    Returns
    -------
    bool
        True if the variable value (case-insensitive, stripped) is one of:
        {"1", "true", "yes", "y", "on", "enabled"}; otherwise False.
    """
    return os.environ.get(name, str(default)).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
        "enabled",
    }


def env_required(name: str) -> str:
    """
    Read a required environment variable.

    Parameters
    ----------
    name:
        Environment variable name.

    Returns
    -------
    str
        The variable value (as-is).

    Raises
    ------
    OSError
        If the variable is unset or empty.
    """
    v = os.environ.get(name)
    if not v:
        raise OSError(f"Missing required env var: {name}")
    return v


def env_optional_str(name: str) -> Optional[str]:
    """
    Read an optional environment variable as a normalized string.

    Parameters
    ----------
    name:
        Environment variable name.

    Returns
    -------
    Optional[str]
        Stripped string value, or None if the variable is unset or one of:
        "", "None", "none", "null".
    """
    v = os.environ.get(name)
    if v is None:
        return None
    v = v.strip()
    if v in ("", "None", "none", "null"):
        return None
    return v


def write_json_atomic(path: str, payload: Mapping[str, Any]) -> None:
    """
    Write a JSON file atomically.

    The payload is written to a temporary file next to `path` and then replaced
    via `os.replace()` to avoid partially-written output files.

    Parameters
    ----------
    path:
        Target JSON file path.
    payload:
        JSON-serializable mapping to write.
    """
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=4, sort_keys=True)
    os.replace(tmp, path)


def write_metadata_file(
    *,
    metadata_file_path: str,
    metadata_payload: Mapping[str, Any],
    metadata_reuse_existing: bool,
) -> None:
    """
    Write a metadata JSON file for dcmqi, optionally reusing an existing file.

    Parameters
    ----------
    metadata_file_path:
        Target path for the JSON metadata file.
    metadata_payload:
        JSON-serializable mapping written to metadata_file_path.
    metadata_reuse_existing:
        If True and metadata_file_path exists, do not overwrite it.

    Raises
    ------
    OSError
        If metadata_file_path exists but is not a regular file (e.g. it is a directory).
    """
    if metadata_reuse_existing and os.path.exists(metadata_file_path):
        if not os.path.isfile(metadata_file_path):
            raise OSError(
                f"Metadata path exists but is not a file: {metadata_file_path}"
            )
        logger.info("Metadata file exists, reusing: %s", metadata_file_path)
        return

    logger.info("Writing metadata JSON: %s", metadata_file_path)
    write_json_atomic(metadata_file_path, metadata_payload)


def validate_and_rootname(path: str) -> str:
    """
    Validate a segmentation file name and return its rootname.

    Parameters
    ----------
    path:
        Path to a segmentation file. Only the file name is used for validation.

    Returns
    -------
    str
        File name with the matched segmentation suffix removed.

    Raises
    ------
    ValueError
        If the file does not end with one of _ALLOWED_SUFFIXES, or if stripping
        the suffix results in an empty rootname.
    """
    name = Path(path).name
    name_lower = name.lower()

    matching = [s for s in _ALLOWED_SUFFIXES if name_lower.endswith(s)]
    if not matching:
        raise ValueError(
            f"Unsupported segmentation file '{name}'. "
            f"Supported: {', '.join(_ALLOWED_SUFFIXES)}"
        )

    matched_suffix = max(matching, key=len)
    root = name[: -len(matched_suffix)].strip().strip(".")
    if not root:
        raise ValueError(f"Invalid segmentation file name '{name}' (empty rootname).")
    return root


def find_segmentation_paths(segmentation_input_dir: str) -> list[str]:
    """
    List segmentation files in a directory (case-insensitive).

    Parameters
    ----------
    segmentation_input_dir:
        Directory that contains segmentation volumes.

    Returns
    -------
    list[str]
        Sorted (case-insensitive) absolute paths of files whose names end with one
        of _ALLOWED_SUFFIXES.

    Raises
    ------
    FileNotFoundError
        If segmentation_input_dir does not exist.
    NotADirectoryError
        If segmentation_input_dir exists but is not a directory.
    """
    base = Path(segmentation_input_dir)
    if not base.exists():
        raise FileNotFoundError(
            f"Segmentation input dir does not exist: {segmentation_input_dir}"
        )
    if not base.is_dir():
        raise NotADirectoryError(
            f"Segmentation input path is not a directory: {segmentation_input_dir}"
        )

    paths = [
        str(p)
        for p in base.iterdir()
        if p.is_file() and p.name.lower().endswith(_ALLOWED_SUFFIXES)
    ]
    return sorted(paths, key=str.lower)


def validate_unique_segmentation_rootnames(segmentation_paths: Sequence[str]) -> None:
    """
    Validate that all segmentation paths resolve to unique rootnames (case-insensitive).

    Rootname collisions are rejected to prevent ambiguous or conflicting outputs.

    Parameters
    ----------
    segmentation_paths:
        Paths to segmentation volumes (e.g. *.nii, *.nii.gz, *.nrrd) that will be
        converted. Each path must have a supported suffix.

    Raises
    ------
    ValueError
        If a path has an unsupported filename/suffix (from validate_and_rootname),
        or if two or more paths resolve to the same rootname (case-insensitive).
    """
    by_root: dict[str, list[str]] = {}
    for p in segmentation_paths:
        root = validate_and_rootname(p)
        by_root.setdefault(root.casefold(), []).append(p)

    collisions = {r: ps for r, ps in by_root.items() if len(ps) > 1}
    if not collisions:
        return

    lines = ["Rootname collisions detected; outputs would conflict:"]
    for r, ps in sorted(collisions.items()):
        lines.append(f"  - {r}:")
        for path in sorted(ps, key=str.lower):
            lines.append(f"      {path}")

    msg = "\n".join(lines)
    logger.error(msg)
    raise ValueError(msg)


def set_or_add(ds: pydicom.Dataset, tag, vr: str, value) -> None:
    """
    Set an existing DICOM element value or add a new one.

    Parameters
    ----------
    ds:
        Target pydicom dataset to modify.
    tag:
        DICOM tag identifying the element (typically a 2-tuple like (0x0018, 0x0015)).
    vr:
        DICOM Value Representation for a new element (e.g. "LO", "CS").
        Ignored if the element already exists.
    value:
        Value to write into the element.

    Notes
    -----
    If the element exists, its value is overwritten. If not, a new element is
    added using the provided VR.
    """
    if tag in ds:
        ds[tag].value = value
    else:
        ds.add_new(tag, vr, value)


def read_trial_and_bodypart(element_input_dir: str) -> tuple[str, Optional[str]]:
    """
    Read the first DICOM file in a directory and extract trial ID and body part.

    The values are taken from:
    - Clinical Trial Protocol ID (0012,0020) -> returned as `aetitle` (fallback: "internal")
    - Body Part Examined (0018,0015)         -> returned as `bodypart` (fallback: None)

    Parameters
    ----------
    element_input_dir:
        Directory containing the reference DICOM series (searched for "*.dcm*").

    Returns
    -------
    aetitle:
        Trial/protocol identifier from (0012,0020), or "internal" if missing/empty.
    bodypart:
        Body part from (0018,0015), or None if missing/empty.

    Raises
    ------
    FileNotFoundError
        If no matching DICOM files are found in `element_input_dir`.
    """
    dcm_files = sorted(
        glob.glob(os.path.join(element_input_dir, "**", "*.dcm*"), recursive=True)
    )
    if not dcm_files:
        raise FileNotFoundError("No dicom file found!")

    ds = pydicom.dcmread(dcm_files[0], stop_before_pixels=True)

    trial_element = ds.get((0x0012, 0x0020))
    aetitle = (
        str(trial_element.value)
        if trial_element and trial_element.value
        else "internal"
    )

    bodypart_element = ds.get((0x0018, 0x0015))
    bodypart = (
        str(bodypart_element.value)
        if bodypart_element and bodypart_element.value
        else None
    )

    return aetitle, bodypart


def write_seg_tags(
    output_dcm_file: str,
    aetitle: str,
    body_part: str,
    dicom_body_part: Optional[str],
) -> None:
    """
    Post-process a created DICOM SEG file and write selected DICOM tags.

    Writes/updates:
    - Body Part Examined (0018,0015)
      - If `body_part` != "N/A", write `body_part`
      - Else if `dicom_body_part` is provided, write `dicom_body_part`
      - Else leave unchanged and log a warning
    - Clinical Trial Protocol ID (0012,0020) from `aetitle` (always written)

    Parameters
    ----------
    output_dcm_file:
        Path to an existing DICOM SEG file to update in-place.
    aetitle:
        Value to write into Clinical Trial Protocol ID (0012,0020).
    body_part:
        Preferred body part value. Use "N/A" to indicate "no explicit body part".
    dicom_body_part:
        Fallback body part (typically extracted from the reference input DICOM series).

    Raises
    ------
    FileNotFoundError
        If `output_dcm_file` does not exist.
    pydicom.errors.InvalidDicomError
        If `output_dcm_file` is not a valid DICOM file.
    """
    ds = pydicom.dcmread(output_dcm_file)

    if body_part == "N/A" and dicom_body_part is not None:
        logger.info(f"# Adding dicom-body_part: {dicom_body_part}")
        set_or_add(ds, (0x0018, 0x0015), "LO", dicom_body_part)
    elif body_part != "N/A":
        logger.info(f"# Adding model-body_part: {body_part}")
        set_or_add(ds, (0x0018, 0x0015), "LO", body_part)
    else:
        logger.warning("# Could not extract any body-part!")

    logger.info(f"# Adding aetitle:   {aetitle}")
    set_or_add(ds, (0x0012, 0x0020), "LO", aetitle)
    ds.save_as(output_dcm_file)


def run_dcmqi(
    *,
    dcmqi_bin_dir: str,
    dcmqi_input_image_list: str,
    dcmqi_input_metadata: str,
    dcmqi_output_dicom: str,
    dcmqi_input_dicom_dir: str,
    dcmqi_skip_empty_slices: bool,
    context: str,
) -> None:
    """
    Execute dcmqi's `itkimage2segimage` and surface output via the logger.

    Parameters
    ----------
    dcmqi_bin_dir:
        Directory containing the `itkimage2segimage` binary.
    dcmqi_input_image_list:
        Either a single segmentation file path, or a comma-separated list of paths
        (for combined/multi-volume conversion).
    dcmqi_input_metadata:
        Path to the dcmqi metadata JSON describing segmentAttributes and series-level fields.
    dcmqi_output_dicom:
        Output path for the resulting DICOM SEG file.
    dcmqi_input_dicom_dir:
        Directory containing the reference DICOM series to associate the SEG with.
    dcmqi_skip_empty_slices:
        If True, add "--skip" to the dcmqi invocation.
    context:
        Short label for log/error messages (e.g. "single-label" or "multi-label").

    Raises
    ------
    FileNotFoundError
        If the dcmqi binary cannot be found (e.g. wrong dcmqi_bin_dir).
    PermissionError
        If the dcmqi binary exists but cannot be executed due to insufficient permissions.
    RuntimeError
        If dcmqi returns a non-zero exit code.
    """
    cmd = [f"{dcmqi_bin_dir}/itkimage2segimage"]
    if dcmqi_skip_empty_slices:
        cmd.append("--skip")
    cmd += [
        "--inputImageList",
        dcmqi_input_image_list,
        "--inputMetadata",
        dcmqi_input_metadata,
        "--outputDICOM",
        dcmqi_output_dicom,
        "--inputDICOMDirectory",
        dcmqi_input_dicom_dir,
    ]

    logger.info("Executing %s", " ".join(cmd))

    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        out_str = (
            out.decode(errors="replace")
            if isinstance(out, (bytes, bytearray))
            else str(out)
        )
        if out_str.strip():
            logger.info(out_str)
    except subprocess.CalledProcessError as spe:
        error_out = (
            spe.output.decode(errors="replace")
            if isinstance(spe.output, (bytes, bytearray))
            else str(spe.output)
        )

        logger.error("dcmqi failed (%s). Command: %s", context, " ".join(cmd))

        if not dcmqi_skip_empty_slices:
            logger.warning(
                "Hint: dcmqi failed without --skip. This can happen with empty slices in the segmentation. "
                "Try enabling SKIP_EMPTY_SLICES=true (note: skipping may affect MITK usability)."
            )

        if error_out.strip():
            logger.error("[dcmqi] Output:\n%s", error_out)

        raise RuntimeError(
            f"dcmqi failed while creating {context} dcm object (exit {spe.returncode})"
        )


# -----------------------------
# Config + orchestration
# -----------------------------
@dataclass(frozen=True)
class OperatorConfig:
    """
    Parsed runtime configuration from environment variables.

    Parameters
    ----------
    dcmqi_bin_dir:
        Directory containing the dcmqi executables. This module invokes:
        "<dcmqi_bin_dir>/itkimage2segimage".
    input_type:
        "multi_label_seg" or "single_label_segs".
    multi_label_seg_name:
        Base name for the combined SEG output.
    multi_label_seg_info_json:
        File name of the multi-label job JSON in OPERATOR_IMAGE_LIST_INPUT_DIR.

    segment_algorithm_name:
        SegmentAlgorithmName written into metadata.
    segment_algorithm_type:
        SegmentAlgorithmType written into metadata.
    content_creator_name:
        ContentCreatorName written into metadata.

    series_description:
        Base SeriesDescription to use (may be overridden in multi-label JSON).
    series_number:
        DICOM SeriesNumber.
    instance_number:
        DICOM InstanceNumber.

    skip_empty_slices:
        If True, call dcmqi with "--skip".
    fail_on_no_segmentation_found:
        If True, fail a batch element when no segmentation files exist.
    reuse_existing_metadata:
        If True, keep existing metadata JSON files and do not overwrite.

    get_seg_info_from_file:
        In single-label mode: True when label name is derived from the filename rootname.
    single_label_seg_info:
        In single-label mode: fixed label name for all segmentations; None if derived from filename.
    create_multi_label_dcm_from_single_label_segs:
        If True, also create one combined SEG from all single-label inputs.

    workflow_dir, batch_name, operator_in_dir, operator_image_list_input_dir, operator_out_dir:
        Directory layout for batch processing.
    """

    dcmqi_bin_dir: str

    input_type: Literal["multi_label_seg", "single_label_segs"]
    multi_label_seg_name: str
    multi_label_seg_info_json: str

    segment_algorithm_name: str
    segment_algorithm_type: str
    content_creator_name: str

    series_description: str
    series_number: int
    instance_number: int

    skip_empty_slices: bool
    fail_on_no_segmentation_found: bool
    reuse_existing_metadata: bool

    get_seg_info_from_file: bool
    single_label_seg_info: Optional[str]
    create_multi_label_dcm_from_single_label_segs: bool

    workflow_dir: str
    batch_name: str
    operator_in_dir: str
    operator_image_list_input_dir: str
    operator_out_dir: str


def load_config() -> OperatorConfig:
    """
    Read, validate, and normalize configuration from environment variables.

    Returns
    -------
    OperatorConfig
        Parsed configuration with defaults applied and required variables enforced.

    Raises
    ------
    OSError
        If required environment variables are missing or empty.
    ValueError
        If INPUT_TYPE has an invalid value, or if SERIES_NUMBER / INSTANCE_NUMBER
        cannot be parsed as integers.
    """
    dcmqi_bin_dir = os.environ.get("DCMQI_BIN_DIR", _DCMQI_DEFAULT_BIN_DIR)

    input_type_raw = os.environ.get("INPUT_TYPE")
    if input_type_raw not in {"multi_label_seg", "single_label_segs"}:
        raise ValueError(
            "INPUT_TYPE must be either 'multi_label_seg' or 'single_label_segs'"
        )
    input_type = cast(Literal["multi_label_seg", "single_label_segs"], input_type_raw)

    multi_label_seg_name = os.environ.get("MULTI_LABEL_SEG_NAME")
    if multi_label_seg_name in (None, "None", ""):
        multi_label_seg_name = "multi-label"

    segment_algorithm_name = os.environ.get("ALGORITHM_NAME", "kaapana")
    segment_algorithm_type = os.environ.get("ALGORITHM_TYPE", "AUTOMATIC")
    content_creator_name = os.environ.get("CREATOR_NAME", "kaapana")

    series_description = os.environ.get("SERIES_DESCRIPTION")
    if series_description in (None, "None", ""):
        series_description = os.environ.get("SERIES_DISCRIPTION", "")

    series_number = int(os.environ.get("SERIES_NUMBER", "300"))
    instance_number = int(os.environ.get("INSTANCE_NUMBER", "1"))

    skip_empty_slices = env_bool("SKIP_EMPTY_SLICES", False)
    fail_on_no_segmentation_found = env_bool("FAIL_ON_NO_SEGMENTATION_FOUND", True)
    reuse_existing_metadata = env_bool("REUSE_EXISTING_METADATA", False)

    multi_label_seg_info_json = os.environ.get(
        "MULTI_LABEL_SEG_INFO_JSON", "seg_info.json"
    )
    if multi_label_seg_info_json in (None, "None", ""):
        multi_label_seg_info_json = "seg_info.json"

    get_seg_info_from_file = False
    single_label_seg_info = env_optional_str("SINGLE_LABEL_SEG_INFO")
    if input_type == "single_label_segs":
        if not single_label_seg_info:
            raise OSError(
                'SINGLE_LABEL_SEG_INFO must be either "from_file_name" or e.g. "right@kidney"'
            )
        if single_label_seg_info.strip().lower() == "from_file_name":
            logger.info("Seg info will be taken from file name")
            get_seg_info_from_file = True
            single_label_seg_info = None

    create_multi_label_dcm_from_single_label_segs = env_bool(
        "CREATE_MULTI_LABEL_DCM_FROM_SINGLE_LABEL_SEGS", False
    )

    workflow_dir = env_required("WORKFLOW_DIR")
    batch_name = env_required("BATCH_NAME")
    operator_in_dir = env_required("OPERATOR_IN_DIR")
    operator_image_list_input_dir = env_required("OPERATOR_IMAGE_LIST_INPUT_DIR")
    operator_out_dir = env_required("OPERATOR_OUT_DIR")

    return OperatorConfig(
        dcmqi_bin_dir=dcmqi_bin_dir,
        input_type=input_type,
        multi_label_seg_name=multi_label_seg_name,
        multi_label_seg_info_json=multi_label_seg_info_json,
        segment_algorithm_name=segment_algorithm_name,
        segment_algorithm_type=segment_algorithm_type,
        content_creator_name=content_creator_name,
        series_description=series_description,
        series_number=series_number,
        instance_number=instance_number,
        skip_empty_slices=skip_empty_slices,
        fail_on_no_segmentation_found=fail_on_no_segmentation_found,
        reuse_existing_metadata=reuse_existing_metadata,
        get_seg_info_from_file=get_seg_info_from_file,
        single_label_seg_info=single_label_seg_info,
        create_multi_label_dcm_from_single_label_segs=create_multi_label_dcm_from_single_label_segs,
        workflow_dir=workflow_dir,
        batch_name=batch_name,
        operator_in_dir=operator_in_dir,
        operator_image_list_input_dir=operator_image_list_input_dir,
        operator_out_dir=operator_out_dir,
    )


def process_single_label_files(
    *,
    cfg: OperatorConfig,
    element_input_dir: str,
    input_image_list_input_dir: str,
    element_output_dir: str,
    segmentation_paths: Sequence[str],
    trial_aetitle: str,
    dicom_body_part: Optional[str],
    base_metadata: Mapping[str, Any],
    series_description: str,
) -> tuple[list[list[Mapping[str, Any]]], int]:
    """
    Convert single-label segmentation volumes into per-file DICOM SEG outputs.

    For each path in `segmentation_paths`, this writes a per-file dcmqi metadata JSON,
    runs dcmqi to create a DICOM SEG, and post-processes the output to set
    Clinical Trial Protocol ID (0012,0020) and Body Part Examined (0018,0015).

    If cfg.create_multi_label_dcm_from_single_label_segs is True, also returns a
    dcmqi-compatible segmentAttributes list-of-lists for combined SEG generation.

    Parameters
    ----------
    cfg:
        Parsed runtime configuration.
    element_input_dir:
        Directory with the reference DICOM series (passed to dcmqi).
    input_image_list_input_dir:
        Directory containing the segmentation files and where metadata JSON is written.
    element_output_dir:
        Output directory for created DICOM SEG files.
    segmentation_paths:
        Segmentation volume paths to convert.
    trial_aetitle:
        Clinical Trial Protocol ID value to write (0012,0020).
    dicom_body_part:
        Body Part Examined (0018,0015) read from the input DICOM series (fallback).
    base_metadata:
        Common dcmqi metadata fields merged into each per-file metadata JSON.
    series_description:
        Base SeriesDescription passed through process_seg_info().

    Returns
    -------
    segment_attributes:
        list-of-lists in dcmqi schema form; populated only when combined generation is enabled.
    created_seg_count:
        Number of per-file DICOM SEG outputs created (excludes any combined SEG).

    Raises
    ------
    RuntimeError
        If SINGLE_LABEL_SEG_INFO is missing/inconsistent for INPUT_TYPE=single_label_segs,
        or if dcmqi fails (non-zero exit code).
    ValueError
        If a segmentation filename has an unsupported suffix (and FAIL_ON_NO_SEGMENTATION_FOUND is enabled).
    OSError
        If writing metadata fails (e.g. metadata path exists but is not a file).
    FileNotFoundError
        If the dcmqi binary cannot be found.
    PermissionError
        If the dcmqi binary exists but cannot be executed due to insufficient permissions.
    """
    processed = 0
    if cfg.single_label_seg_info is None and not cfg.get_seg_info_from_file:
        raise RuntimeError(
            "SINGLE_LABEL_SEG_INFO is required for INPUT_TYPE=single_label_segs"
        )

    segment_attributes: list[list[Mapping[str, Any]]] = []
    cmap = cm.get_cmap("gist_ncar", max(len(segmentation_paths), 1))

    for idx, seg_filepath in enumerate(segmentation_paths):
        logger.debug(f"process idx: {idx} - {seg_filepath}")

        try:
            rootname = validate_and_rootname(seg_filepath)
        except ValueError as e:
            logger.error(str(e))
            if cfg.fail_on_no_segmentation_found:
                raise
            continue

        single_label_seg_info = (
            rootname
            if cfg.get_seg_info_from_file
            else (cfg.single_label_seg_info or rootname)
        )

        code_meaning, series_desc = process_seg_info(
            single_label_seg_info, series_description
        )
        color = np.round(np.array(cmap(idx)[:3]) * 255).astype(int).tolist()

        segment_attribute = create_segment_attribute(
            cfg.segment_algorithm_type,
            cfg.segment_algorithm_name,
            code_meaning,
            color,
        )

        if cfg.create_multi_label_dcm_from_single_label_segs:
            segment_attributes.append([segment_attribute])

        metadata = {
            **base_metadata,
            "SeriesDescription": series_desc,
            "segmentAttributes": [[segment_attribute]],
        }

        meta_data_file = os.path.join(input_image_list_input_dir, f"{rootname}.json")
        write_metadata_file(
            metadata_file_path=meta_data_file,
            metadata_payload=metadata,
            metadata_reuse_existing=cfg.reuse_existing_metadata,
        )

        output_dcm_file = os.path.join(element_output_dir, f"{rootname}.dcm")
        logger.debug(f"Starting dcmqi-subprocess for: {output_dcm_file}")
        logger.debug(f"skip_empty_slices: {cfg.skip_empty_slices}")

        run_dcmqi(
            dcmqi_bin_dir=cfg.dcmqi_bin_dir,
            dcmqi_input_image_list=seg_filepath,
            dcmqi_input_metadata=meta_data_file,
            dcmqi_output_dicom=output_dcm_file,
            dcmqi_input_dicom_dir=element_input_dir,
            dcmqi_skip_empty_slices=cfg.skip_empty_slices,
            context="single-label",
        )

        write_seg_tags(
            output_dcm_file,
            aetitle=trial_aetitle,
            body_part="N/A",
            dicom_body_part=dicom_body_part,
        )
        processed += 1

    return segment_attributes, processed


def build_multi_label_segment_attributes(
    *,
    cfg: OperatorConfig,
    input_image_list_input_dir: str,
    series_description: str,
    segmentation_paths: Sequence[str],
) -> tuple[list[list[Mapping[str, Any]]], str, str]:
    """
    Build dcmqi `segmentAttributes` from the multi-label job JSON (seg_info).

    Reads cfg.multi_label_seg_info_json from `input_image_list_input_dir`, normalizes
    its "seg_info" via normalize_seg_info(), and converts it into dcmqi schema
    list-of-lists of segment attribute dicts.

    Group-to-file mapping (validated):
    - If one segmentation volume is provided, seg_info must normalize to exactly one group.
    - If multiple volumes are provided, seg_info must normalize to N groups where N equals
      len(segmentation_paths); group order must match the sorted input file order.

    Overrides:
    - If JSON contains "algorithm", returns an updated series_description:
        - if series_description is set:
            "<series_description> | algorithm=<ALGORITHM_NAME>-<algorithm>"
        - otherwise:
            "<ALGORITHM_NAME>-<algorithm>"
    - Returns body_part from JSON "task_body_part" if present, else "N/A".

    Notes:
    - label_int == 0 is treated as background and skipped.

    Parameters
    ----------
    cfg:
        Parsed runtime configuration (provides JSON filename and algorithm settings).
    input_image_list_input_dir:
        Directory containing the multi-label job JSON and segmentation volumes.
    series_description:
        Base SeriesDescription (may be overridden by JSON "algorithm").
    segmentation_paths:
        Sorted list of segmentation volume paths used for validating group mapping.

    Returns
    -------
    segment_attributes:
        dcmqi schema list-of-lists of segment attribute dicts (one inner list per group).
    series_description:
        Possibly overridden SeriesDescription.
    body_part:
        "task_body_part" from JSON or "N/A".

    Raises
    ------
    FileNotFoundError
        If the multi-label job JSON file is missing.
    KeyError
        If the JSON does not contain the key "seg_info".
    ValueError
        If the seg_info group-to-file mapping is invalid (group count does not match the number
        of segmentation volumes).
    """
    json_path = os.path.join(input_image_list_input_dir, cfg.multi_label_seg_info_json)
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"Missing multi-label seg info json: {json_path}")
    with open(json_path) as f:
        data = json.load(f)

    if "seg_info" not in data:
        raise KeyError(f"Could not find key 'seg_info' in json-file: {json_path}")

    seg_info_ll = normalize_seg_info(seg_info=data["seg_info"])

    # Validate that seg_info groups align with the provided input volumes:
    # - 1 volume  -> exactly 1 group
    # - N volumes -> exactly N groups, matching the sorted file order
    if len(segmentation_paths) == 1:
        if len(seg_info_ll) != 1:
            raise ValueError(
                f"seg_info defines {len(seg_info_ll)} groups but found 1 segmentation file. "
                "For a single multi-label volume, seg_info must be a single group (list[str] / list[dict])."
            )
    else:
        if len(seg_info_ll) != len(segmentation_paths):
            raise ValueError(
                f"seg_info defines {len(seg_info_ll)} groups but found {len(segmentation_paths)} segmentation files. "
                "For multiple input volumes, seg_info must be list[list[...]] with one group per file, "
                "matching the sorted file order."
            )

    # Allow per-job series description customization (useful for model/version tagging).
    if "algorithm" in data:
        algo_suffix = f"{cfg.segment_algorithm_name}-{str(data['algorithm']).strip()}"
        series_description = (
            f"{series_description} | algorithm={algo_suffix}"
            if series_description
            else algo_suffix
        )

    segment_attributes: list[list[Mapping[str, Any]]] = [[] for _ in seg_info_ll]

    for l_idx, label_info in enumerate(seg_info_ll):
        label_counts = len(label_info)
        cmap_local = cm.get_cmap("gist_ncar", max(label_counts, 1))

        for idx, label in enumerate(label_info):
            label_int = int(label["label_int"])
            label_name = label["label_name"]

            logger.debug(f"process: {label_name}: {label_int}")
            # label_int==0 is reserved for background; dcmqi expects segments to start at 1.
            if label_int == 0:
                logger.debug("Background Label -> skipping")
                continue

            code_meaning, _ = process_seg_info(label_name, series_description)
            color = np.round(np.array(cmap_local(idx)[:3]) * 255).astype(int).tolist()

            segment_attribute = create_segment_attribute(
                cfg.segment_algorithm_type,
                cfg.segment_algorithm_name,
                code_meaning,
                color,
                label_name=label_name,
                labelID=label_int,
            )
            segment_attributes[l_idx].append(segment_attribute)

    # task_body_part (if provided) overrides Body Part Examined in the final SEG.
    body_part = data.get("task_body_part", "N/A")
    return segment_attributes, series_description, body_part


def generate_combined_seg(
    *,
    cfg: OperatorConfig,
    element_input_dir: str,
    input_image_list_input_dir: str,
    element_output_dir: str,
    segmentation_paths: Sequence[str],
    trial_aetitle: str,
    dicom_body_part: Optional[str],
    base_metadata: Mapping[str, Any],
    series_description: str,
    segment_attributes: list[list[Mapping[str, Any]]],
    body_part: str,
) -> None:
    """
    Create a combined DICOM SEG for one batch element from one or more segmentation volumes.

    Parameters
    ----------
    cfg:
        Parsed runtime configuration.
    element_input_dir:
        Directory containing the reference DICOM series used for dcmqi's --inputDICOMDirectory.
    input_image_list_input_dir:
        Directory where the metadata JSON for the combined SEG is written.
    element_output_dir:
        Output directory where the combined SEG (".dcm") is written.
    segmentation_paths:
        Segmentation volume paths to pass to dcmqi (comma-joined for --inputImageList).
    trial_aetitle:
        Value written into Clinical Trial Protocol ID (0012,0020) of the output SEG.
    dicom_body_part:
        Body Part Examined (0018,0015) read from the reference DICOM series (fallback).
    base_metadata:
        Base dcmqi metadata fields (schema, creator, series/instance numbers).
    series_description:
        Base SeriesDescription used to derive the combined SeriesDescription.
    segment_attributes:
        dcmqi `segmentAttributes` list-of-lists describing segments/groups for the combined SEG.
    body_part:
        Body part override written into (0018,0015) when not "N/A"; otherwise `dicom_body_part`
        is used when available.

    Raises
    ------
    RuntimeError
        Propagated from run_dcmqi() if dcmqi fails to create the combined SEG.
    FileNotFoundError
        Propagated from run_dcmqi() if the dcmqi binary cannot be found.
    PermissionError
        Propagated from run_dcmqi() if the dcmqi binary cannot be executed due to permissions.
    OSError
        If writing metadata fails (e.g. metadata path exists but is not a file).
    """
    _, combined_series_desc = process_seg_info(
        cfg.multi_label_seg_name, series_description
    )

    metadata = {
        **base_metadata,
        "SeriesDescription": combined_series_desc,
        "segmentAttributes": segment_attributes,
    }

    meta_data_file = os.path.join(
        input_image_list_input_dir, f"{cfg.multi_label_seg_name.lower()}.json"
    )
    write_metadata_file(
        metadata_file_path=meta_data_file,
        metadata_payload=metadata,
        metadata_reuse_existing=cfg.reuse_existing_metadata,
    )

    output_dcm_file = os.path.join(
        element_output_dir, f"{cfg.multi_label_seg_name.lower()}.dcm"
    )
    logger.info(f"Output SEG.dcm file:: {output_dcm_file}")
    logger.info(f"Starting dcmqi-subprocess for: {output_dcm_file}")
    logger.info(f"skip_empty_slices: {cfg.skip_empty_slices}")

    run_dcmqi(
        dcmqi_bin_dir=cfg.dcmqi_bin_dir,
        dcmqi_input_image_list=",".join(segmentation_paths),
        dcmqi_input_metadata=meta_data_file,
        dcmqi_output_dicom=output_dcm_file,
        dcmqi_input_dicom_dir=element_input_dir,
        dcmqi_skip_empty_slices=cfg.skip_empty_slices,
        context="multi-label",
    )

    write_seg_tags(
        output_dcm_file,
        aetitle=trial_aetitle,
        body_part=body_part,
        dicom_body_part=dicom_body_part,
    )


def process_batch(cfg: OperatorConfig, batch_element_dir: str) -> int:
    """
    Process one batch element directory (one "case") and create DICOM SEG outputs.

    Parameters
    ----------
    cfg:
        Parsed runtime configuration.
    batch_element_dir:
        Absolute/relative path to a single batch element directory. The function expects
        the configured subdirectories to exist under this path:
        - cfg.operator_in_dir (reference DICOM series)
        - cfg.operator_image_list_input_dir (segmentation volumes + optional seg_info JSON)
        - cfg.operator_out_dir (output SEG files)

    Returns
    -------
    int
        Number of created DICOM SEG files (".dcm") for this batch element:
        - single-label mode: one per segmentation file (+1 if combined generation is enabled)
        - multi-label mode: exactly 1 combined SEG

    Raises
    ------
    FileNotFoundError
        If no reference DICOM files are found, if no segmentation files are found and
        FAIL_ON_NO_SEGMENTATION_FOUND is enabled, if required multi-label JSON is missing,
        or if the dcmqi binary cannot be found (wrong DCMQI_BIN_DIR).
    PermissionError
        If the dcmqi binary exists but cannot be executed due to insufficient permissions.
    OSError
        If writing metadata fails (e.g. metadata path exists but is not a file).
    ValueError
        If a segmentation filename has an unsupported suffix, if rootname collisions exist,
        or if multi-label seg_info mapping is invalid.
    KeyError
        If the multi-label job JSON does not contain the key "seg_info".
    RuntimeError
        If dcmqi fails to create the DICOM SEG.
    """
    element_input_dir = os.path.join(batch_element_dir, cfg.operator_in_dir)
    input_image_list_input_dir = os.path.join(
        batch_element_dir, cfg.operator_image_list_input_dir
    )
    element_output_dir = os.path.join(batch_element_dir, cfg.operator_out_dir)
    os.makedirs(element_output_dir, exist_ok=True)

    trial_aetitle, dicom_body_part = read_trial_and_bodypart(element_input_dir)
    try:
        segmentation_paths = find_segmentation_paths(input_image_list_input_dir)
    except (FileNotFoundError, NotADirectoryError) as e:
        logger.debug("Segmentation directory issue: %s", e)
        segmentation_paths = []

    if not segmentation_paths:
        msg = (
            f"Could not find valid segmentation file in {input_image_list_input_dir}. "
            "Supported: '*.nii', '*.nii.gz', '*.nrrd'"
        )

        if cfg.fail_on_no_segmentation_found:
            logger.error(msg)
            raise FileNotFoundError("No segmentation files found")

        logger.warning(msg)
        logger.info("Skipping %s!", input_image_list_input_dir)
        return 0

    validate_unique_segmentation_rootnames(segmentation_paths)

    base_metadata = {
        "@schema": "https://raw.githubusercontent.com/qiicr/dcmqi/master/doc/schemas/seg-schema.json#",
        "ContentCreatorName": cfg.content_creator_name,
        "SeriesNumber": int(cfg.series_number),
        "InstanceNumber": int(cfg.instance_number),
    }

    # this can be overridden in multi-label json (task_body_part)
    body_part = "N/A"
    series_description = cfg.series_description

    processed = 0
    segment_attributes: list[list[Mapping[str, Any]]] = []

    if cfg.input_type == "single_label_segs":
        segment_attributes, processed_single = process_single_label_files(
            cfg=cfg,
            element_input_dir=element_input_dir,
            input_image_list_input_dir=input_image_list_input_dir,
            element_output_dir=element_output_dir,
            segmentation_paths=segmentation_paths,
            trial_aetitle=trial_aetitle,
            dicom_body_part=dicom_body_part,
            base_metadata=base_metadata,
            series_description=series_description,
        )
        processed += processed_single

        if cfg.create_multi_label_dcm_from_single_label_segs and not segment_attributes:
            msg = "Requested combined SEG from single-label segs, but no valid segmentations were found."
            if cfg.fail_on_no_segmentation_found:
                raise FileNotFoundError(msg)
            logger.info(msg)
            return processed

    elif cfg.input_type == "multi_label_seg":
        segment_attributes, series_description, body_part = (
            build_multi_label_segment_attributes(
                cfg=cfg,
                input_image_list_input_dir=input_image_list_input_dir,
                series_description=series_description,
                segmentation_paths=segmentation_paths,
            )
        )

    # Multi-label mode is all-or-nothing: any config/data issue should fail the batch element
    # rather than producing partial outputs.
    # Combined generation is isolated here
    if (
        cfg.input_type == "multi_label_seg"
        or cfg.create_multi_label_dcm_from_single_label_segs
    ):
        generate_combined_seg(
            cfg=cfg,
            element_input_dir=element_input_dir,
            input_image_list_input_dir=input_image_list_input_dir,
            element_output_dir=element_output_dir,
            segmentation_paths=segmentation_paths,
            trial_aetitle=trial_aetitle,
            dicom_body_part=dicom_body_part,
            base_metadata=base_metadata,
            series_description=series_description,
            segment_attributes=segment_attributes,
            body_part=body_part,
        )
        processed += 1

    return processed


def main() -> int:
    """
    Entry point: load configuration, iterate over batch elements, and return an exit code.

    The batch root directory is built as "/<WORKFLOW_DIR>/<BATCH_NAME>/", and each direct
    child folder is treated as one batch element ("case"). For each batch element,
    `process_batch()` is invoked.

    Returns
    -------
    int
        Process exit code:
        - 0 if at least one DICOM SEG file (".dcm") was created across all batch elements
        - 1 if no outputs were created

    Notes
    -----
    `processed_count` counts created DICOM SEG output files (".dcm"), not input volumes.
    """
    logger.info("Started: 'itkimage2segimage'")
    cfg = load_config()

    batch_root = os.path.join("/", cfg.workflow_dir, cfg.batch_name)
    batch_folders = sorted(glob.glob(os.path.join(batch_root, "*")))
    logger.info(f"Found {len(batch_folders)} batches")

    processed_count = 0  # counts created ".dcm" SEG outputs
    for batch_element_dir in batch_folders:
        logger.info(f"process: {batch_element_dir}")
        processed_count += process_batch(cfg, batch_element_dir)

    logger.info("#\n#\n#\n#")
    logger.info(f"# Created SEG files: {processed_count}")
    logger.info("#\n#")

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
        return 1

    logger.info("#")
    logger.info(f"# ----> {processed_count} FILES HAVE BEEN CREATED!")
    logger.info("#")
    logger.info("# DONE #")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
