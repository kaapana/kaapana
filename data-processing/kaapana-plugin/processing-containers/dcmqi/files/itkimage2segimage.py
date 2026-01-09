import os
import json
import glob
from matplotlib import cm
import subprocess
import numpy as np
import pydicom
from pathlib import Path
from typing import Any, Mapping
import logging
from kaapanapy.logger import get_logger

from metadata_helper import (
    create_segment_attribute,
    process_seg_info,
    normalize_seg_info,
)

# Logger
logger = get_logger(__name__, logging.INFO)

processed_count = 0

_ALLOWED_SUFFIXES = (".nrrd", ".nii", ".nii.gz")


def set_or_add(ds, tag, vr, value):
    if tag in ds:
        ds[tag].value = value
    else:
        ds.add_new(tag, vr, value)


def adding_aetitle(output_dcm_file, aetitle, body_part, dicom_body_part):
    dcmseg_file = pydicom.dcmread(output_dcm_file)

    if body_part == "N/A" and dicom_body_part is not None:
        print(f"# Adding dicom-body_part: {dicom_body_part}")
        set_or_add(dcmseg_file, (0x0018, 0x0015), "LO", dicom_body_part)
    elif body_part != "N/A":
        print(f"# Adding model-body_part: {body_part}")
        set_or_add(dcmseg_file, (0x0018, 0x0015), "LO", body_part)
    else:
        print("# Could not extract any body-part!")

    print(f"# Adding aetitle:   {aetitle}")
    set_or_add(
        dcmseg_file, (0x0012, 0x0020), "LO", aetitle
    )  # Clinical Trial Protocol ID
    dcmseg_file.save_as(output_dcm_file)


def read_trial_and_bodypart(element_input_dir: str) -> tuple[str, str | None]:
    dcm_files = sorted(
        glob.glob(os.path.join(element_input_dir, "*.dcm*"), recursive=True)
    )
    if not dcm_files:
        raise FileNotFoundError("No dicom file found!")
    dcmseg_file = pydicom.dcmread(dcm_files[0], stop_before_pixels=True)

    trial_element = dcmseg_file.get((0x0012, 0x0020))
    aetitle = (
        str(trial_element.value)
        if trial_element and trial_element.value
        else "internal"
    )

    bodypart_element = dcmseg_file.get((0x0018, 0x0015))
    bodypart = (
        str(bodypart_element.value)
        if bodypart_element and bodypart_element.value
        else None
    )

    return aetitle, bodypart


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
        "enabled",
    }


def env_required(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise AssertionError(f"Missing required env var: {name}")
    return v


def run_dcmqi(
    *,
    dcmqi_bin_dir: str,
    dcmqi_input_image_list: str,
    dcmqi_input_metadata: str,
    dcmqi_output_dicom: str,
    dcmqi_input_dicom_dir: str,
    dcmqi_skip_empty_slices: bool,
    context: str,  # e.g. "single-label" / "multi-label" for messages
) -> None:
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

    print("Executing", " ".join(cmd))

    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        out_str = (
            out.decode(errors="replace")
            if isinstance(out, (bytes, bytearray))
            else str(out)
        )
        if out_str.strip():
            print(out_str)
    except subprocess.CalledProcessError as spe:
        raw_output = spe.output
        error_out = (
            raw_output.decode(errors="replace")
            if isinstance(raw_output, (bytes, bytearray))
            else str(raw_output)
        )
        if not dcmqi_skip_empty_slices:
            # Original text, only substituted the raw output to the parsed one.
            # print(
            #     f"The image seems to have empty slices, we will skip them! This might make the segmentation no usable anymore for MITK. Error: {error_out}"
            # )

            # New Output with much clearer hinting
            print(
                "Hint: dcmqi failed without --skip. This can happen with empty slices in the segmentation. "
                "Try enabling SKIP_EMPTY_SLICES=true (note: skipping may affect MITK usability)."
            )

        if error_out.strip():
            print(f"[dcmqi] Output:\n{error_out}")

        raise AssertionError(
            f"Something went wrong while creating the {context} dcm object.\n"
            f"Command: {' '.join(cmd)}\n"
            f"Exit code: {spe.returncode}\n"
            f"Output:\n{error_out}"
        )


def validate_and_rootname(path: str) -> str:
    """
    Validate supported segmentation extensions and return rootname.
    Supports: .nrrd, .nii, .nii.gz
    Raises ValueError on unsupported file names.
    """
    p = Path(path)
    name_lower = p.name.lower()

    # validate
    if not name_lower.endswith(_ALLOWED_SUFFIXES):
        raise ValueError(
            f"Unsupported segmentation file '{p.name}'. "
            f"Supported: {', '.join(_ALLOWED_SUFFIXES)}"
        )

    # extract rootname
    root = None
    if name_lower.endswith(".nii.gz"):
        root = p.name[: -len(".nii.gz")]
    elif name_lower.endswith(".nii"):
        root = p.name[: -len(".nii")]
    else:  # .nrrd
        root = p.name[: -len(".nrrd")]

    root = root.strip().strip(".")
    if not root:
        raise ValueError(f"Invalid segmentation file name '{p.name}' (empty rootname).")
    return root


def write_json_atomic(path: str, payload: Mapping[str, Any]) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=4, sort_keys=True)
    os.replace(tmp, path)


# Example: https://github.com/QIICR/dcmqi/blob/master/doc/examples/seg-example.json
# SegmentedPropertyCategoryCodeSequence: Sequence defining the general category of the property the segment represents: https://dicom.innolitics.com/ciods/rt-structure-set/rt-roi-observations/30060080/00620003
# SegmentedPropertyTypeCodeSequence: https://dicom.innolitics.com/ciods/segmentation/segmentation-image/00620002/0062000f
# Note
# "Property" is used in the sense of meaning "what the segmented voxels represent", whether it be a physical or biological object, be real or conceptual, having spatial, temporal or functional extent or not. I.e., it is what the segment "is" (as opposed to some feature, attribute, quality, or characteristic of it, like color or shape or size).
# Only a single Item shall be included in this Sequence.
# http://dicom.nema.org/medical/dicom/current/output/chtml/part16/chapter_L.html#chapter_L


print("Started: 'itkimage2segimage' ")
DCMQI = "/kaapana/app/dcmqi/bin"


# os.environ['BATCH_NAME'] = 'batch'
# os.environ['OPERATOR_IN_DIR'] = 'input'
# os.environ['WORKFLOW_DIR'] = '/home/klaus/private_data/jip-data/dcmqi/nnunet_test-200727123756236842/'

# # Case 1 single label segs with seg info
# os.environ['INPUT_TYPE'] = 'single_label_segs'
# os.environ['OPERATOR_IMAGE_LIST_INPUT_DIR'] = 'nnunet-predict_case1'
# os.environ['OPERATOR_OUT_DIR'] = 'nrrd2dcmseg_case1'
# os.environ['SINGLE_LABEL_SEG_INFO'] = 'right@kidney'

# # Case 2 single label seg info from file name
# os.environ['INPUT_TYPE'] = 'single_label_segs'
# os.environ['OPERATOR_IMAGE_LIST_INPUT_DIR'] = 'nnunet-predict_case2'
# os.environ['OPERATOR_OUT_DIR'] = 'nrrd2dcmseg_case2'
# os.environ['SINGLE_LABEL_SEG_INFO'] = 'from_file_name'

# # Case 3 Multiple single labels with creating of multi seg
# os.environ['INPUT_TYPE'] = 'single_label_segs'
# os.environ['OPERATOR_IMAGE_LIST_INPUT_DIR'] = 'nnunet-predict_case3'
# os.environ['OPERATOR_OUT_DIR'] = 'nrrd2dcmseg_case3'
# os.environ['SINGLE_LABEL_SEG_INFO'] = 'from_file_name'
# os.environ['CREATE_MULIT_LABEL_DCM_FROM_SINGLE_LABEL_SEGS'] = 'True'

# # Case 4 Multi label label segs input
# os.environ['INPUT_TYPE'] = 'multi_label_seg'
# os.environ['OPERATOR_IMAGE_LIST_INPUT_DIR'] = 'nnunet-predict_case4'
# os.environ['OPERATOR_OUT_DIR'] = 'nrrd2dcmseg_case4'
# os.environ['MULTI_LABEL_SEG_INFO_JSON'] = 'layer_info'
# os.environ['MULTI_LABEL_SEG_NAME'] = 'example multilabel'

# If input type is set to "multi_label_seg" you must create a json inside the OPERATOR_IMAGE_LIST_INPUT_DIR that contains the parts as follows: {"seg_info": ["spleen", "right@kidney"]}

input_type = os.environ.get("INPUT_TYPE")  # multi_label_seg or single_label_segs
multi_label_seg_name = (
    os.environ.get("MULTI_LABEL_SEG_NAME")
    if os.environ.get("MULTI_LABEL_SEG_NAME") not in [None, "None", ""]
    else "multi-label"
)  # Name used for multi-label segmentation object, if it will be created
segment_algorithm_name = os.environ.get("ALGORITHM_NAME", "kaapana")
segment_algorithm_type = os.environ.get("ALGORITHM_TYPE", "AUTOMATIC")
content_creator_name = os.environ.get("CREATOR_NAME", "kaapana")
series_description = os.environ.get("SERIES_DISCRIPTION", "")
series_number = os.environ.get("SERIES_NUMBER", "300")
instance_number = os.environ.get("INSTANCE_NUMBER", "1")
skip_empty_slices = env_bool("SKIP_EMPTY_SLICES", False)
fail_on_no_segmentation_found = env_bool("FAIL_ON_NO_SEGMENTATION_FOUND", True)
reuse_existing_metadata = env_bool("REUSE_EXISTING_METADATA", False)

get_seg_info_from_file = False
if input_type == "multi_label_seg":
    multi_label_seg_info_json = os.environ.get(
        "MULTI_LABEL_SEG_INFO_JSON", "seg_info.json"
    )  # name of json file that contain the parts as follows e.g. {"seg_info": ["spleen", "right@kidney"]}

    if multi_label_seg_info_json in [None, "None", ""]:
        multi_label_seg_info_json = "seg_info.json"

elif input_type == "single_label_segs":
    single_label_seg_info = os.environ.get(
        "SINGLE_LABEL_SEG_INFO"
    )  # SINGLE_LABEL_SEG_INFO must be either "from_file_name" or a e.g. "right@kidney"
    if single_label_seg_info == "":
        raise AssertionError(
            'SINGLE_LABEL_SEG_INFO must be either "from_file_name" or a e.g. "right@kidney"]}'
        )
    elif single_label_seg_info == "from_file_name":
        print("Seg info will be taken from file name")
        get_seg_info_from_file = True
    else:
        print(f"Taking {single_label_seg_info} as seg info")
else:
    raise NameError("Input_type must be either multi_label_seg or single_label_segs")

create_multi_label_dcm_from_single_label_segs = env_bool(
    "CREATE_MULIT_LABEL_DCM_FROM_SINGLE_LABEL_SEGS", False
)  # true or false

# Needed env vars for all cases that do not have defaults
workflow_dir = env_required("WORKFLOW_DIR")
batch_name = env_required("BATCH_NAME")
operator_in_dir = env_required("OPERATOR_IN_DIR")
operator_image_list_input_dir = env_required("OPERATOR_IMAGE_LIST_INPUT_DIR")
operator_out_dir = env_required("OPERATOR_OUT_DIR")

batch_folders = sorted(
    [f for f in glob.glob(os.path.join("/", workflow_dir, batch_name, "*"))]
)

print("Found {} batches".format(len(batch_folders)))

for batch_element_dir in batch_folders:
    print("process: {}".format(batch_element_dir))

    body_part = "N/A"

    element_input_dir = os.path.join(batch_element_dir, operator_in_dir)
    input_image_list_input_dir = os.path.join(
        batch_element_dir, operator_image_list_input_dir
    )
    trial_aetitle, dicom_body_part = read_trial_and_bodypart(element_input_dir)
    element_output_dir = os.path.join(batch_element_dir, operator_out_dir)
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)

    segmentation_paths = []
    for endings in ("*.nii", "*.nii.gz", "*.nrrd"):
        segmentation_paths.extend(glob.glob(f"{input_image_list_input_dir}/{endings}"))

    if len(segmentation_paths) == 0:
        print(
            "Could not find valid segmentation file in {}".format(
                input_image_list_input_dir
            )
        )
        print("Supported: '*.nii', '*.nii.gz', '*.nrrd'")
        if fail_on_no_segmentation_found:
            print("abort!")
            exit(1)
        else:
            print(f"Skipping {input_image_list_input_dir}!")
            continue
    segmentation_paths = sorted(segmentation_paths, key=str.lower)

    base_metadata = {
        "@schema": "https://raw.githubusercontent.com/qiicr/dcmqi/master/doc/schemas/seg-schema.json#",
        "ContentCreatorName": content_creator_name,
        "SeriesNumber": int(series_number),
        "InstanceNumber": int(instance_number),
    }
    segment_attributes = []

    if input_type == "single_label_segs":
        print("input_type == 'single_label_segs'")

        cmap = cm.get_cmap("gist_ncar", max(len(segmentation_paths), 1))
        for idx, seg_filepath in enumerate(segmentation_paths):
            print(f"process idx: {idx} - {seg_filepath}")

            try:
                rootname = validate_and_rootname(seg_filepath)
            except ValueError as e:
                print(str(e))
                if fail_on_no_segmentation_found:
                    exit(1)
                else:
                    continue

            if get_seg_info_from_file is True:
                single_label_seg_info = rootname

            (code_meaning, series_desc) = process_seg_info(
                single_label_seg_info, series_description
            )
            color = np.round(np.array(cmap(idx)[:3]) * 255).astype(int).tolist()
            segment_attribute = create_segment_attribute(
                segment_algorithm_type, segment_algorithm_name, code_meaning, color
            )

            if create_multi_label_dcm_from_single_label_segs:
                segment_attributes.append([segment_attribute])

            metadata = {
                **base_metadata,
                "SeriesDescription": series_desc,
                "segmentAttributes": [[segment_attribute]],
            }
            meta_data_file = f"{input_image_list_input_dir}/{rootname}.json"
            if reuse_existing_metadata and os.path.isfile(meta_data_file):
                print(
                    f"Wow, meta data file exsists already, taking this one: {meta_data_file}"
                )
            else:
                print("Writing JSON:: {}".format(meta_data_file))
                write_json_atomic(meta_data_file, metadata)

            # Creating dcm_object
            output_dcm_file = f"{element_output_dir}/{rootname}.dcm"

            print("Starting dcmqi-subprocess for: {}".format(output_dcm_file))
            print(f"skip_empty_slices: {skip_empty_slices}")
            run_dcmqi(
                dcmqi_bin_dir=DCMQI,
                dcmqi_input_image_list=seg_filepath,
                dcmqi_input_metadata=meta_data_file,
                dcmqi_output_dicom=output_dcm_file,
                dcmqi_input_dicom_dir=element_input_dir,
                dcmqi_skip_empty_slices=skip_empty_slices,
                context="single-label",
            )
            adding_aetitle(
                output_dcm_file,
                aetitle=trial_aetitle,
                body_part=body_part,
                dicom_body_part=dicom_body_part,
            )
            processed_count += 1

        if create_multi_label_dcm_from_single_label_segs and not segment_attributes:
            msg = "Requested combined SEG from single-label segs, but no valid segmentations were found."
            if fail_on_no_segmentation_found:
                raise AssertionError(msg)
            else:
                print(msg)
                continue

    elif input_type == "multi_label_seg":
        print("input_type == 'multi_label_seg'")

        json_path = os.path.join(input_image_list_input_dir, multi_label_seg_info_json)
        with open(json_path) as f:
            data = json.load(f)

        print("Loaded seg_info", data)

        if "seg_info" not in data:
            print(f"Could not find key 'seg_info' in json-file: {json_path}")
            print("Abort!")
            exit(1)

        seg_info = data["seg_info"]
        seg_info_ll = normalize_seg_info(seg_info=seg_info)

        body_part = "N/A"
        if "task_body_part" in data:
            body_part = data["task_body_part"]

        if "algorithm" in data:
            series_description = "{}-{}".format(
                segment_algorithm_name, data["algorithm"]
            )

        segment_attributes = [[] for _ in seg_info_ll]

        for l_idx, label_info in enumerate(seg_info_ll):
            label_counts = len(label_info)
            for idx, label in enumerate(label_info):
                label_int = int(label["label_int"])
                single_label_seg_info = label["label_name"]
                print(f"process: {single_label_seg_info}: {label_int}")
                if label_int == 0:
                    print("Clear Label -> skipping")
                    continue

                (code_meaning, _) = process_seg_info(
                    single_label_seg_info, series_description
                )
                color = (
                    np.round(
                        np.array(cm.get_cmap("gist_ncar", label_counts)(idx)[:3]) * 255
                    )
                    .astype(int)
                    .tolist()
                )
                segment_attribute = create_segment_attribute(
                    segment_algorithm_type,
                    segment_algorithm_name,
                    code_meaning,
                    color,
                    label_name=single_label_seg_info,
                    labelID=label_int,
                )
                segment_attributes[l_idx].append(segment_attribute)

    if input_type == "multi_label_seg" or create_multi_label_dcm_from_single_label_segs:
        _, combined_series_desc = process_seg_info(
            multi_label_seg_name, series_description
        )

        metadata = {
            **base_metadata,
            "SeriesDescription": combined_series_desc,
            "segmentAttributes": segment_attributes,
        }
        meta_data_file = (
            f"{input_image_list_input_dir}/{multi_label_seg_name.lower()}.json"
        )
        if reuse_existing_metadata and os.path.isfile(meta_data_file):
            print(
                f"Wow, meta data file exsists already, taking this one: {meta_data_file}"
            )
        else:
            print("Writing JSON:: {}".format(meta_data_file))
            write_json_atomic(meta_data_file, metadata)

        output_dcm_file = f"{element_output_dir}/{multi_label_seg_name.lower()}.dcm"
        print("Output SEG.dcm file:: {}".format(output_dcm_file))
        print("Starting dcmqi-subprocess for: {}".format(output_dcm_file))
        print(f"skip_empty_slices: {skip_empty_slices}")
        run_dcmqi(
            dcmqi_bin_dir=DCMQI,
            dcmqi_input_image_list=",".join(segmentation_paths),
            dcmqi_input_metadata=meta_data_file,
            dcmqi_output_dicom=output_dcm_file,
            dcmqi_input_dicom_dir=element_input_dir,
            dcmqi_skip_empty_slices=skip_empty_slices,
            context="multi-label",
        )
        adding_aetitle(
            output_dcm_file,
            aetitle=trial_aetitle,
            body_part=body_part,
            dicom_body_part=dicom_body_part,
        )
        processed_count += 1


print("#")
print("#")
print("#")
print("#")
print(f"# Processed file_count: {processed_count}")
print("#")
print("#")
if processed_count == 0:
    print("#")
    print("##################################################")
    print("#")
    print("##################  ERROR  #######################")
    print("#")
    print("# ----> NO FILES HAVE BEEN PROCESSED!")
    print("#")
    print("##################################################")
    print("#")
    exit(1)
else:
    print("#")
    print(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
    print("#")
    print("# DONE #")
