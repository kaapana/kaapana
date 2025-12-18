import json
import math
import logging
from kaapanapy.logger import get_logger

# Logger
logger = get_logger(__name__, logging.INFO)

# Metadata JSON
PLACEHOLDER_CODING_SCHEME_DESIGNATOR = "Custom"
PLACEHOLDER_CODE_VALUE = "0.0.0.0.0.0.00000.0.000.0.00"

code_lookup_table_path = "code_lookup_table.json"
with open(code_lookup_table_path) as f:
    code_lookup_table = json.load(f)


def find_code_meaning(tag):
    logger.info("#####################################################")
    logger.info("#")
    logger.info(f"Searching for identical hit for {tag}...")

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
    code_meaning = str(seg_info).lower()
    series_description_code_meaning = f"{code_meaning}"

    if series_description != "":
        return code_meaning, series_description
    else:
        return code_meaning, series_description_code_meaning


def create_segment_attribute(
    segment_algorithm_type,
    segment_algorithm_name,
    code_meaning,
    color,
    label_name="",
    labelID=1,
):
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
    segment_attribute["labelID"] = labelID
    segment_attribute["SegmentAlgorithmType"] = segment_algorithm_type
    segment_attribute["SegmentAlgorithmName"] = segment_algorithm_name
    segment_attribute["recommendedDisplayRGBValue"] = color

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
    default_color=[128, 0, 0],
):
    """
    Maps a list of label entries to a list of segment attribute dictionaries.

    Args:
        label_entries (list): List of dicts with 'label_int' and 'label_name'
        segment_algorithm_type (str): DICOM value for algorithm type
        segment_algorithm_name (str): Name of the algorithm used
        default_color (list): RGB list used for all labels (can be extended later)

    Returns:
        list: List of segment attribute dictionaries
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
    Wraps pre-built segment attributes into the standard DICOM segmentation metadata format.

    Args:
        segment_attributes (list of list): Nested list of segment attribute dicts.
        content_creator_name (str): Name of the person or system creating the content.
        series_number (int): DICOM series number.
        instance_number (int): DICOM instance number.
        series_description (str): Description for the DICOM series.

    Returns:
        dict: DICOM-compatible segmentation metadata dictionary.
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
