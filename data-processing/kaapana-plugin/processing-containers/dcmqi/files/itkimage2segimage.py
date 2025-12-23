import os
import json
import glob
import re
import math
import random
from matplotlib import cm
import subprocess
import numpy as np
import pydicom

from metadata_helper import (
    create_segment_attribute,
    process_seg_info,
    normalize_seg_info,
)

processed_count = 0


def adding_aetitle(element_input_dir, output_dcm_file, body_part):
    dcm_files = sorted(
        glob.glob(os.path.join(element_input_dir, "*.dcm*"), recursive=True)
    )

    if len(dcm_files) == 0:
        print("No dicom file found!")
        exit(1)

    dcm_file = dcm_files[0]
    print("dcm-file: {}".format(dcm_file))
    input_dicom = pydicom.dcmread(dcm_file)
    try:
        aetitle = input_dicom[0x0012, 0x0020].value
    except KeyError:
        aetitle = "internal"
    try:
        dicom_body_part = input_dicom[0x0018, 0x0015].value
    except KeyError:
        dicom_body_part = None

    dcmseg_file = pydicom.dcmread(output_dcm_file)
    print(f"# Adding aetitle:   {aetitle}")
    if body_part == "N/A" and dicom_body_part is not None:
        print(f"# Adding dicom-body_part: {dicom_body_part}")
        dcmseg_file.add_new(
            [0x0018, 0x0015], "LO", dicom_body_part
        )  # Body Part Examined
    elif body_part != "N/A":
        print(f"# Adding model-body_part: {body_part}")
        dcmseg_file.add_new([0x0018, 0x0015], "LO", body_part)  # Body Part Examined
    else:
        print("# Could not extract any body-part!")

    dcmseg_file.add_new([0x0012, 0x0020], "LO", aetitle)  # Clinical Trial Protocol ID
    dcmseg_file.save_as(output_dcm_file)


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
skip_empty_slices = (
    True if os.environ.get("SKIP_EMPTY_SLICES", "false").lower() == "true" else False
)
fail_on_no_segmentation_found = (
    True
    if os.environ.get("FAIL_ON_NO_SEGMENTATION_FOUND", "true").lower() == "true"
    else False
)

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
    create_multi_label_dcm_from_single_label_segs = os.environ.get(
        "CREATE_MULIT_LABEL_DCM_FROM_SINGLE_LABEL_SEGS", "false"
    )  # true or false
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


batch_folders = sorted(
    [
        f
        for f in glob.glob(
            os.path.join("/", os.environ["WORKFLOW_DIR"], os.environ["BATCH_NAME"], "*")
        )
    ]
)

print("Found {} batches".format(len(batch_folders)))

for batch_element_dir in batch_folders:
    print("process: {}".format(batch_element_dir))

    element_input_dir = os.path.join(batch_element_dir, os.environ["OPERATOR_IN_DIR"])
    input_image_list_input_dir = os.path.join(
        batch_element_dir, os.environ["OPERATOR_IMAGE_LIST_INPUT_DIR"]
    )

    element_output_dir = os.path.join(batch_element_dir, os.environ["OPERATOR_OUT_DIR"])
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

    base_metadata = {
        "@schema": "https://raw.githubusercontent.com/qiicr/dcmqi/master/doc/schemas/seg-schema.json#",
        "ContentCreatorName": content_creator_name,
        "SeriesNumber": int(series_number),
        "InstanceNumber": int(instance_number),
    }

    if input_type == "single_label_segs":
        print("input_type == 'single_label_segs'")

        segment_attributes = []
        for idx, seg_filepath in enumerate(segmentation_paths):
            print(f"process idx: {idx} - {seg_filepath}")

            seg_filename = os.path.basename(seg_filepath)
            m = re.compile(r"(.*?)(\.nii.gz|\.nii|\.nrrd)").search(seg_filename)
            rootname = m.groups()[-2]

            if get_seg_info_from_file is True:
                single_label_seg_info = rootname

            (code_meaning, series_desc) = process_seg_info(
                single_label_seg_info, series_description
            )
            color = (
                np.round(
                    np.array(cm.get_cmap("gist_ncar", 20)(random.randint(0, 19))[:3])
                    * 255
                )
                .astype(int)
                .tolist()
            )
            segment_attribute = create_segment_attribute(
                segment_algorithm_type, segment_algorithm_name, code_meaning, color
            )

            if create_multi_label_dcm_from_single_label_segs.lower() == "true":
                segment_attributes.append([segment_attribute])

            metadata = {
                **base_metadata,
                "SeriesDescription": series_desc,
                "segmentAttributes": [[segment_attribute]],
            }
            meta_data_file = f"{input_image_list_input_dir}/{rootname}.json"
            if os.path.isfile(meta_data_file):
                print("Wow, meta data file exsists already, taking this one!")
            else:
                with open(meta_data_file, "w") as write_file:
                    print("Writing JSON:: {}".format(meta_data_file))
                    json.dump(metadata, write_file, indent=4, sort_keys=True)

            # Creating dcm_object
            output_dcm_file = f"{element_output_dir}/{rootname}.dcm"

            print("Starting dcmqi-subprocess for: {}".format(output_dcm_file))
            print(f"skip_empty_slices: {skip_empty_slices}")
            if skip_empty_slices:
                try:
                    dcmqi_command = [
                        f"{DCMQI}/itkimage2segimage",
                        "--skip",
                        "--inputImageList",
                        seg_filepath,
                        "--inputMetadata",
                        meta_data_file,
                        "--outputDICOM",
                        output_dcm_file,
                        "--inputDICOMDirectory",
                        element_input_dir,
                    ]
                    print("Executing", " ".join(dcmqi_command))
                    resp = subprocess.check_output(
                        dcmqi_command, stderr=subprocess.STDOUT
                    )
                    print(resp)
                except subprocess.CalledProcessError as e:
                    raise AssertionError(
                        f"Something weng wrong while creating the single-label-dcm object {e.output}"
                    )
            else:
                try:
                    dcmqi_command = [
                        f"{DCMQI}/itkimage2segimage",
                        "--inputImageList",
                        seg_filepath,
                        "--inputMetadata",
                        meta_data_file,
                        "--outputDICOM",
                        output_dcm_file,
                        "--inputDICOMDirectory",
                        element_input_dir,
                    ]
                    print("Executing", " ".join(dcmqi_command))
                    resp = subprocess.check_output(
                        dcmqi_command, stderr=subprocess.STDOUT
                    )
                    print(resp)
                except subprocess.CalledProcessError as e:
                    print(
                        f"The image seems to have empty slices, we will skip them! This might make the segmentation no usable anymore for MITK. Error: {e.output}"
                    )
                    raise AssertionError(
                        f"Something weng wrong while creating the single-label-dcm object {e.output}"
                    )

            adding_aetitle(element_input_dir, output_dcm_file, body_part="N/A")
            processed_count += 1

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

    if (
        input_type == "multi_label_seg"
        or create_multi_label_dcm_from_single_label_segs.lower() == "true"
    ):
        _, combined_series_desc = process_seg_info(
            multi_label_seg_name, series_description
        )

        metadata = metadata = {
            **base_metadata,
            "SeriesDescription": combined_series_desc,
            "segmentAttributes": segment_attributes,
        }
        meta_data_file = (
            f"{input_image_list_input_dir}/{multi_label_seg_name.lower()}.json"
        )
        if os.path.isfile(meta_data_file):
            print("Wow, meta data file exsists already, taking this one!")
        else:
            with open(meta_data_file, "w") as write_file:
                print("Writing JSON:: {}".format(meta_data_file))
                json.dump(metadata, write_file, indent=4, sort_keys=True)

        output_dcm_file = f"{element_output_dir}/{multi_label_seg_name.lower()}.dcm"
        print("Output SEG.dcm file:: {}".format(output_dcm_file))
        print("Starting dcmqi-subprocess for: {}".format(output_dcm_file))
        print(f"skip_empty_slices: {skip_empty_slices}")
        if skip_empty_slices:
            try:
                dcmqi_command = [
                    f"{DCMQI}/itkimage2segimage",
                    "--skip",
                    "--inputImageList",
                    ",".join(segmentation_paths),
                    "--inputMetadata",
                    meta_data_file,
                    "--outputDICOM",
                    output_dcm_file,
                    "--inputDICOMDirectory",
                    element_input_dir,
                ]
                print("Executing", " ".join(dcmqi_command))
                resp = subprocess.check_output(dcmqi_command, stderr=subprocess.STDOUT)
                print(resp)
            except subprocess.CalledProcessError as e:
                raise AssertionError(
                    f"Something weng wrong while creating the multi-label-dcm object {e.output}"
                )
        else:
            try:
                dcmqi_command = [
                    f"{DCMQI}/itkimage2segimage",
                    "--inputImageList",
                    ",".join(segmentation_paths),
                    "--inputMetadata",
                    meta_data_file,
                    "--outputDICOM",
                    output_dcm_file,
                    "--inputDICOMDirectory",
                    element_input_dir,
                ]
                print("Executing", " ".join(dcmqi_command))
                resp = subprocess.check_output(dcmqi_command, stderr=subprocess.STDOUT)
                print(resp)
            except subprocess.CalledProcessError as e:
                print(
                    f"The image seems to have emtpy slices, we will skip them! This might make the segmentation no usable anymore for MITK. Error: {e.output}"
                )
                raise AssertionError(
                    f"Something weng wrong while creating the multi-label-dcm object {e.output}"
                )

        adding_aetitle(element_input_dir, output_dcm_file, body_part=body_part)
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
