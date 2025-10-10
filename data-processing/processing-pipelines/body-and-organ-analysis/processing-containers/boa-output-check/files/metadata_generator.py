import json
import math

# Metadata JSON

code_lookup_table_path = "code_lookup_table.json"
with open(code_lookup_table_path) as f:
    code_lookup_table = json.load(f)


def find_code_meaning(tag):
    result = None
    print("#####################################################")
    print("#")
    print(f"Searching for identical hit for {tag}...")
    tag = tag.lower()
    for entry in code_lookup_table:
        if tag.replace(" ", "-") == entry["Code Meaning"].lower().replace(" ", "-"):
            print(
                f"Found Code Meaning: {entry['Code Meaning'].lower()} for search term: {tag}"
            )
            result = entry
            break
        elif tag == entry["Body Part Examined"].lower():
            print(
                f"Found Code Meaning: {entry['Body Part Examined'].lower()} for search term: {tag}"
            )
            result = entry
            break

    if result == None:
        print(f"Nothing found -> Searching if {tag} is in one of the entires...")
        for entry in code_lookup_table:
            if tag in entry["Code Meaning"].lower():
                print(
                    f"Found Code Meaning: {entry['Code Meaning'].lower()} for search term: {tag}"
                )
                result = entry
                break
            elif tag in entry["Body Part Examined"].lower():
                print(
                    f"Found Code Meaning: {entry['Body Part Examined'].lower()} for search term: {tag}"
                )
                result = entry
                break

    if result == None:
        print(f"Nothing found -> Searching if {tag} parts equals one of the entires...")
        for entry in code_lookup_table:
            for tag_part in tag.split(" "):
                if tag_part == entry["Code Meaning"].lower():
                    print(
                        f"Found Code Meaning: {entry['Code Meaning'].lower()} for search term: {tag_part.lower()}"
                    )
                    result = entry
                    break
                elif tag_part == entry["Body Part Examined"].lower():
                    print(
                        f"Found Code Meaning: {entry['Body Part Examined'].lower()} for search term: {tag_part.lower()}"
                    )
                    result = entry
                    break
            if result != None:
                break

    if result == None:
        print(
            f"Nothing found -> Searching if {tag} parts can be found in one of the entires..."
        )
        for entry in code_lookup_table:
            for tag_part in tag.split(" "):
                if tag_part in entry["Code Meaning"].lower():
                    print(
                        f"Found Code Meaning: {entry['Code Meaning'].lower()} for search term: {tag_part.lower()}"
                    )
                    result = entry
                    break
                elif tag_part in entry["Body Part Examined"].lower():
                    print(
                        f"Found Code Meaning: {entry['Body Part Examined'].lower()} for search term: {tag_part.lower()}"
                    )
                    result = entry
                    break
            if result != None:
                break

    if result == None:
        print(
            f"Could not find the tag: '{tag}' in the lookup table, using custom entry"
        )
        result = {
            "Coding Scheme Designator": "Custom",
            "Code Value": "0.0.0.0.0.0.00000.0.000.0.00",
            "Code Meaning": f"{tag.replace('  ', ' '). lower()}",
            "Body Part Examined": "",
            "SNOMED-RT ID (Retired)": "",
            "FMA Code Value": None,
            "UMLS Concept UniqueID": "",
        }

    print("#")
    print("#####################################################")
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
        print("Searching coding-scheme for code-meaning: {}".format(code_meaning))
        print("Search-key: {}".format(search_key))
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
    segment_attribute["SegmentedPropertyTypeModifierCodeSequence"] = {
        "CodeValue": str(coding_scheme["Code Value"]),
        "CodingSchemeDesignator": (
            coding_scheme["SNOMED-RT ID (Retired)"] if not math.isnan else "unknown"
        ),
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
