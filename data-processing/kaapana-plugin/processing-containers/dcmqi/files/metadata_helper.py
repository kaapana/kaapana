"""
Helpers for building dcmqi DICOM SEG metadata
============================================

This module contains utility functions used by the itkimage2segimage conversion
script to build dcmqi-compatible SEG metadata structures.

Main responsibilities
---------------------
- Code lookup:
  Resolve a label/body-part tag to a coding-scheme entry from `code_lookup_table.json`.
  If no match is found, a placeholder "Custom" coding scheme is used.

- Segment attribute construction:
  Build dcmqi `segmentAttributes` entries (per label) and wrap them into the full
  segmentation metadata JSON structure expected by dcmqi.

- seg_info normalization:
  Normalize flexible user/job input (`seg_info`) into the strict list-of-lists of
  label dicts required by the dcmqi schema. Supports explicit or generated label IDs
  and enforces background rules (label_int == 0 only for background names).

Files
-----
- code_lookup_table.json:
  Lookup table used for resolving coding information. It is loaded once at import.

Notes
-----
- If a lookup entry is found but missing required coding fields, the entry is
  intentionally filled with placeholders (mutating the in-memory lookup object).
"""

import json
import math
import logging
from pathlib import Path
from typing import Sequence
from kaapanapy.logger import get_logger

# Logger
logger = get_logger(__name__, logging.INFO)

# Metadata JSON
PLACEHOLDER_CODING_SCHEME_DESIGNATOR = "Custom"
PLACEHOLDER_CODE_VALUE = "0.0.0.0.0.0.00000.0.000.0.00"

_CODE_LOOKUP_TABLE_PATH = Path(__file__).with_name("code_lookup_table.json")

with _CODE_LOOKUP_TABLE_PATH.open() as f:
    code_lookup_table = json.load(f)


def find_code_meaning(tag):
    """
    Find a coding-scheme entry for a given tag/name.

    The lookup checks the loaded `code_lookup_table` using several match strategies:
    exact match, partial match, and word-level matches (case-insensitive).

    If no entry matches, a "Custom" placeholder entry is returned.
    If an entry matches but is missing required fields ("Coding Scheme Designator" or
    "Code Value"), those fields are overwritten with placeholder values (intentional mutation).

    Parameters
    ----------
    tag:
        Search term (e.g. label name, body part), case-insensitive.

    Returns
    -------
    Mapping[str, Any]
        Lookup entry (possibly placeholder, possibly mutated to fill required fields).
    """
    logger.debug("#####################################################")
    logger.debug("#")
    logger.debug(f"Searching for identical hit for {tag}...")

    # Normalize input (case and whitespace)
    tag = tag.lower().strip()
    tag_hyphen = tag.replace(" ", "-")
    tag_parts = tag.split()

    result = None

    for entry in code_lookup_table:
        code_meaning = entry["Code Meaning"].lower()
        body_part = entry["Body Part Examined"].lower()
        code_meaning_hyphen = code_meaning.replace(" ", "-")

        # 1. Exact match (with or without hyphens)
        if (tag_hyphen == code_meaning_hyphen) or (tag == body_part):
            logger.info(
                f"Found Code Meaning: {entry['Code Meaning']} for search term: {tag}"
            )
            result = entry
            break

        # 2. Partial match (tag contained in either field)
        if (tag in code_meaning) or (tag in body_part):
            logger.info(
                f"Found Code Meaning: {entry['Code Meaning']} for search term: {tag}"
            )
            result = entry
            break

        # 3. Word-level exact match
        if any((tp == code_meaning) or (tp == body_part) for tp in tag_parts):
            logger.info(
                f"Found Code Meaning: {entry['Code Meaning']} for word in search term: {tag}"
            )
            result = entry
            break

        # 4. Word-level partial match
        if any((tp in code_meaning) or (tp in body_part) for tp in tag_parts):
            logger.info(
                f"Found Code Meaning: {entry['Code Meaning']} for word in search term: {tag}"
            )
            result = entry
            break

    # 5a. If nothing found — create a custom entry
    if result is None:
        logger.info(
            f"Could not find the tag: '{tag}' in the lookup table, using custom entry"
        )
        result = {
            "Coding Scheme Designator": "Custom",
            "Code Value": "0.0.0.0.0.0.00000.0.000.0.00",
            "Code Meaning": " ".join(tag.split()),  # safely collapse multiple spaces
            "Body Part Examined": "",
            "SNOMED-RT ID (Retired)": "",
            "FMA Code Value": None,
            "UMLS Concept UniqueID": "",
        }

    # 5b. If found but incomplete — warn and overwrite with placeholders
    # (this mutates the in-memory lookup entry, which is intentional)
    if not result.get("Coding Scheme Designator") or not result.get("Code Value"):
        logger.warning(
            "Lookup entry for tag '%s' has missing Code Value or Coding Scheme "
            "Designator. Overwriting with placeholders. Entry was: %s",
            tag,
            result,
        )
        if not result.get("Coding Scheme Designator"):
            result["Coding Scheme Designator"] = PLACEHOLDER_CODING_SCHEME_DESIGNATOR
        if not result.get("Code Value"):
            result["Code Value"] = PLACEHOLDER_CODE_VALUE

    logger.info("#")
    logger.info("#####################################################")
    return result


def process_seg_info(seg_info, series_description):
    """
    Normalize seg_info and ensure a SeriesDescription is present.

    Parameters
    ----------
    seg_info:
        Label/segment identifier (any type; converted to string).
    series_description:
        Base SeriesDescription. If empty, a default description derived from seg_info is used.

    Returns
    -------
    (code_meaning, series_description)
        code_meaning is always lowercased string form of seg_info.
        series_description is either the provided one or a derived default.
    """
    code_meaning = str(seg_info).lower()
    default_series_description = f"{code_meaning}"
    if series_description != "":
        return code_meaning, series_description
    return code_meaning, default_series_description


def create_segment_attribute(
    segment_algorithm_type,
    segment_algorithm_name,
    code_meaning,
    color,
    label_name="",
    labelID=1,
):
    """
    Create a dcmqi-compatible segmentAttributes entry for one label.

    Parameters
    ----------
    segment_algorithm_type:
        DICOM SegmentAlgorithmType (e.g. "AUTOMATIC").
    segment_algorithm_name:
        DICOM SegmentAlgorithmName.
    code_meaning:
        Label meaning used for lookup and written into CodeMeaning.
    color:
        RGB triplet (3 ints) used as recommendedDisplayRGBValue.
    label_name:
        SegmentLabel value.
    labelID:
        labelID written into the segment attributes.

    Returns
    -------
    dict[str, Any]
        Segment attribute dictionary in dcmqi schema style.

    Raises
    ------
    AssertionError
        If lookup table access fails in an unexpected way.
    """
    try:
        search_key = (
            code_meaning.split("@")[-1].lower() if "@" in code_meaning else code_meaning
        )
        logger.info("Searching coding-scheme for code-meaning: {}".format(code_meaning))
        logger.info("Search-key: {}".format(search_key))
        coding_scheme = find_code_meaning(tag=search_key)
    except KeyError:
        raise AssertionError(
            f"The specified code meaning {code_meaning.lower()} does not exist. Check here for available code names: http://dicom.nema.org/medical/dicom/current/output/chtml/part16/chapter_L.html#chapter_L from Table L-1."
        )

    segment_attribute = {}
    segment_attribute["labelID"] = int(labelID)
    segment_attribute["SegmentAlgorithmType"] = segment_algorithm_type
    segment_attribute["SegmentAlgorithmName"] = segment_algorithm_name
    segment_attribute["recommendedDisplayRGBValue"] = list(color)

    # segment_attribute["SegmentNumber"] = labelID
    segment_attribute["SegmentLabel"] = label_name
    segment_attribute["SegmentedPropertyCategoryCodeSequence"] = {
        "CodeValue": str(coding_scheme["Code Value"]),
        "CodingSchemeDesignator": coding_scheme["Coding Scheme Designator"],
        "CodeMeaning": code_meaning,
    }
    segment_attribute["SegmentedPropertyTypeCodeSequence"] = {
        "CodeValue": str(coding_scheme["Code Value"]),
        "CodingSchemeDesignator": coding_scheme["Coding Scheme Designator"],
        "CodeMeaning": code_meaning,
    }
    coding_value = coding_scheme.get("SNOMED-RT ID (Retired)")
    # Check if it's a number and not NaN
    if isinstance(coding_value, (int, float)) and not math.isnan(coding_value):
        coding_scheme_designator = coding_value
    else:
        coding_scheme_designator = "unknown"
    segment_attribute["SegmentedPropertyTypeModifierCodeSequence"] = {
        "CodeValue": str(coding_scheme["Code Value"]),
        "CodingSchemeDesignator": coding_scheme_designator,
        "CodeMeaning": code_meaning,
    }
    return segment_attribute


def map_labels_to_segment_attributes(
    label_entries,
    segment_algorithm_type="AUTOMATIC",
    segment_algorithm_name="kaapana",
    default_color: Sequence[int] = [128, 0, 0],  # RGB triplet
):
    """
    Map label entries to segmentAttributes entries.

    Parameters
    ----------
    label_entries:
        Iterable of dicts with keys: "label_int" and "label_name".
    segment_algorithm_type:
        SegmentAlgorithmType used for all labels.
    segment_algorithm_name:
        SegmentAlgorithmName used for all labels.
    default_color:
        RGB triplet used for all labels.

    Returns
    -------
    list[dict[str, Any]]
        One segmentAttributes dict per label entry.
    """
    segment_attributes = []
    for entry in label_entries:
        label_id = entry["label_int"]
        label_name = entry["label_name"]
        code_meaning = label_name.replace("_", " ").capitalize()

        seg_attr = create_segment_attribute(
            segment_algorithm_type=segment_algorithm_type,
            segment_algorithm_name=segment_algorithm_name,
            code_meaning=code_meaning,
            color=default_color,
            label_name=label_name,
            labelID=label_id,
        )
        segment_attributes.append(seg_attr)

    return segment_attributes


def build_segmentation_information(
    segment_attributes,
    series_description,
    content_creator_name="kaapana",
    series_number=300,
    instance_number=1,
):
    """
    Wrap segmentAttributes into the standard dcmqi segmentation metadata dict.

    Parameters
    ----------
    segment_attributes:
        Nested list structure (list-of-lists) of segmentAttributes entries.
    series_description:
        SeriesDescription written into the metadata.
    content_creator_name:
        ContentCreatorName written into the metadata.
    series_number:
        DICOM SeriesNumber.
    instance_number:
        DICOM InstanceNumber.

    Returns
    -------
    dict[str, Any]
        dcmqi-compatible segmentation metadata mapping.
    """
    segmentation_information = {
        "@schema": "https://raw.githubusercontent.com/qiicr/dcmqi/master/doc/schemas/seg-schema.json#",
        "ContentCreatorName": content_creator_name,
        "SeriesNumber": series_number,
        "InstanceNumber": instance_number,
        "SeriesDescription": series_description,
        "segmentAttributes": segment_attributes,  # already structured correctly
    }
    return segmentation_information


def normalize_seg_info(seg_info, background_names=("background", "__background__")):
    """
    Normalize seg_info into dcmqi-compatible list-of-groups: list[list[dict]].

    Accepted input shapes (all normalize to list[list[{"label_name","label_int"}]]):
      - dict                               -> [[dict]]
      - list[str] / list[dict]             -> [list]
      - list[list[str]] / list[list[dict]] -> list-of-groups

    Rules:
      - label_int is all-or-none per group:
          * if any label in a group provides label_int, all labels in that group must provide it
          * otherwise label_int is generated starting at 1 per group
      - label_int == 0 is reserved for background only (label_name must match background_names, case-insensitive).
      - label_int < 0 is invalid.
      - Extra keys in label dicts are preserved; duplicates are not checked.

    Parameters
    ----------
    seg_info:
        Label description(s) in one of the accepted input shapes.
    background_names:
        Names allowed to use label_int=0 (case-insensitive).

    Returns
    -------
    list[list[dict]]
        Normalized list-of-groups structure.

    Raises
    ------
    TypeError
        If seg_info is neither dict nor list.
    ValueError
        If seg_info has an unsupported/mixed shape, a label is missing a valid name,
        a group mixes explicit/missing label_int, or label_int violates background/negativity rules.
    """
    # 0) Prebuild some later used set:
    #    Allowed names that may legally use label_int == 0 (background).
    allowed_bg = {n.strip().lower() for n in background_names}

    # 1) Normalize the outer shape into "groups": list[list[...]].
    #    Each group becomes a list of label entries (strings or dicts).
    if isinstance(seg_info, dict):
        groups = [[seg_info]]
    elif isinstance(seg_info, list):
        if not seg_info:
            return []
        if all(isinstance(x, str) for x in seg_info):  # list[str]
            groups = [seg_info]
        elif all(isinstance(x, dict) for x in seg_info):  # list[dict]
            groups = [seg_info]
        elif all(isinstance(x, list) for x in seg_info):  # list[list[...]]
            groups = seg_info
        else:
            raise ValueError("Unsupported seg_info: mixed types in top-level list")
    else:
        raise TypeError(f"seg_info must be dict or list, got {type(seg_info).__name__}")

    # 2) Convert each group to list[dict], enforcing all-or-none label_int per group.
    seg_info_ll: list[list[dict]] = []

    for group in groups:
        if not isinstance(group, list):
            raise ValueError("Expected each group to be a list")

        out_group: list[dict] = []
        seen_explicit = False
        seen_missing = False
        next_id = 1  # start at 1; 0 is reserved for background

        tmp_items: list[dict] = []
        for item in group:
            if isinstance(item, str):
                seen_missing = True
                tmp_items.append({"label_name": item})
                continue

            if isinstance(item, dict):
                label = dict(item)

                name = label.get("label_name", label.get("label"))
                if not isinstance(name, str) or not name.strip():
                    raise ValueError(f"Label dict missing a valid name: {item}")
                label["label_name"] = name

                if label.get("label_int") is None:
                    seen_missing = True
                else:
                    seen_explicit = True

                tmp_items.append(label)
                continue

            raise ValueError(f"Unsupported label entry type: {type(item).__name__}")

        if seen_explicit and seen_missing:
            raise ValueError(
                "Mixed label_int usage within a group: either set label_int for all labels "
                "in the group, or omit label_int for all labels in the group."
            )

        for label in tmp_items:
            name = label["label_name"].strip()

            if seen_explicit:
                label_int = int(label["label_int"])
                label["label_int"] = label_int
            else:
                label["label_int"] = next_id
                label_int = next_id
                next_id += 1

            if label_int == 0:
                if name.lower() not in allowed_bg:
                    raise ValueError(
                        f"label_int=0 is reserved for background, but got label_name={name!r}"
                    )
            elif label_int < 0:
                raise ValueError(f"label_int must be >= 0, got {label_int}")

            out_group.append(label)

        seg_info_ll.append(out_group)

    return seg_info_ll
