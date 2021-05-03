import os
from os import getenv, remove
from os.path import join, exists, dirname, basename
from glob import glob
from shutil import copy2, move, rmtree
from pathlib import Path
import shutil
import nibabel as nib
import numpy as np
import json

# For multiprocessing
from multiprocessing.pool import ThreadPool

# For shell-execution
from subprocess import PIPE, run

from numpy.lib.function_base import delete
execution_timeout = 120

# Counter to check if smth has been processed
processed_count = 0
merged_counter = 0

skipped_dict = {
    "segmentation_files":[],
    "base_images":[]
}


def create_metadata_json(new_labels_dict):
    metadata_dict = {
        "segmentAttributes": []
    }

    for key, new_label in new_labels_dict.items():
        metadata_dict["segmentAttributes"].append(
            [{
                "SegmentLabel": str(new_label),
                "TrackingIdentifier": str(new_label),
                "labelID": int(key),
            }]
        )

    return metadata_dict


def check_overlapping(gt_map, new_map):
    gt_map = np.where(gt_map != 0, 1, gt_map)
    new_map = np.where(new_map != 0, 1, new_map)

    agg_arr = gt_map + new_map
    max_value = int(np.amax(agg_arr))
    if max_value > 1:
        print("# Overlapping Segmentations!!!")
        # overlapping_indexes = np.where(agg_arr > 1)
        return True, agg_arr > 1
    else:
        return False, None


def merge_niftis(queue_dict):
    global global_labels_info, merged_counter, delete_merged_data, fail_if_overlapping, skipping_level, skipped_dict

    target_dir = queue_dict["target_dir"]
    base_image_path = queue_dict["base_image"]
    seg_nifti_list = queue_dict["seg_files"]
    multi = queue_dict["multi"]

    base_image_loaded = nib.load(base_image_path)
    example_img_path = seg_nifti_list[0]
    example_img = nib.load(example_img_path)
    example_dimensions = example_img.shape
    new_gt_map = np.zeros_like(example_img.get_fdata().astype(int))
    local_gt_map_labels = list(np.unique(new_gt_map))
    local_labels_info = {}

    print("#")
    print("#")
    print("##################################################")
    print("#")
    print(f"#### Processing images for base-image:")
    print(f"#### {base_image_path}")
    print("#")
    print("##################################################")
    print("#")
    print("#")

    for seg_nifti in seg_nifti_list:
        print(f"# Processing NIFTI: {basename(seg_nifti)}")
        print("#")
        extracted_label_tag = None
        seg_id = None
        extracted_label_tag = None
        print("#")
        if "--" in seg_nifti:
            seg_info = seg_nifti.split("--")
            extracted_label_tag = seg_info[-1].split(".")[0].replace("_", " ").replace("++", "/")
            seg_id = seg_info[1]

        meta_info_json_path = glob(join(dirname(seg_nifti), "*.json"), recursive=False)
        if len(meta_info_json_path) == 1 and exists(meta_info_json_path[0]):
            meta_info_json_path = meta_info_json_path[0]
            print(f"# Found DCMQI meta-json: {meta_info_json_path}")
            with open(meta_info_json_path, 'rb') as f:
                meta_info = json.load(f)

            if "segmentAttributes" in meta_info:
                for entries in meta_info["segmentAttributes"]:
                    for part in entries:
                        if "labelID" in part and (seg_id is None or str(part["labelID"]) == seg_id):
                            if "labelID" in part and seg_id is None:
                                seg_id = int(part["labelID"])
                            if "SegmentLabel" in part:
                                print("# Using 'SegmentLabel' !")
                                extracted_label_tag = part["SegmentLabel"]

                            elif "TrackingIdentifier" in part:
                                print("# Using 'TrackingIdentifier' !")
                                extracted_label_tag = part["TrackingIdentifier"]

        print(f"# SEG_ID: {seg_id}")
        print(f"# extracted_label_tag: {extracted_label_tag}")

        if extracted_label_tag is None:
            print("#")
            print("#")
            print("####### Could not extract label encoding from file!")
            print("#")
            print("#")
            return queue_dict, "extracted_label_tag is None"
        if seg_id is None:
            print("#")
            print("#")
            print("####### Could not extract seg_id!")
            print("#")
            print("#")
            return queue_dict, "seg_id is None"

        if extracted_label_tag in list(local_labels_info.values()):
            print("#")
            print("#")
            print("##################################################")
            print("#")
            print(f"#### {extracted_label_tag} is already present in the gt-merge!")
            print("#### -> skipping segmentation")
            print("#")
            print("##################################################")
            print("#")
            print("#")
            continue

        seg_id = int(seg_id)

        loaded_seg_nifti = nib.load(seg_nifti).get_fdata().astype(int)
        nifti_labels = list(np.unique(loaded_seg_nifti))
        nifti_dimensions = loaded_seg_nifti.shape
        if len(nifti_labels) == 1 and 0 in nifti_labels:
            print("#")
            print("##################################################")
            print("#")
            print("######### No segmentation in NIFTI found!")
            print(f"# -> Skipping {extracted_label_tag}")
            print("#")
            print("##################################################")
            print("#")
            print("#")
            continue

        assert len(nifti_labels) == 2 and seg_id in nifti_labels

        if example_dimensions != nifti_dimensions:
            print("# Issue with different dimensions in seg-NIFTIS!")
            print("# -> starting resampling..")
            resampling_success = resample_image(input_path=seg_nifti, original_path=example_img_path)
            if not resampling_success:
                return queue_dict, "resampling failed"
            print("# -> checking dimensions ...")
            loaded_seg_nifti = nib.load(seg_nifti).get_fdata().astype(int)
            nifti_labels = list(np.unique(loaded_seg_nifti))
            nifti_dimensions = loaded_seg_nifti.shape
            assert example_dimensions == nifti_dimensions

        new_global_id = False
        global_label_id = None
        if extracted_label_tag in global_labels_info:
            print("# This label is already present in global label-dict!")
            global_label_id = global_labels_info[extracted_label_tag]
        else:
            new_global_id = True
            global_label_id = len(global_labels_info.values())+1
            global_labels_info[extracted_label_tag] = global_label_id
            print(f"# This label NOT present in global label-dict -> adding {global_label_id}")

        if seg_id != global_label_id:
            print(f"# Found {seg_id} global label: {global_label_id}")
            print(f"# Replacing labels: {extracted_label_tag} -> from {seg_id} to {global_label_id}")
            assert global_label_id not in local_gt_map_labels
            loaded_seg_nifti = np.where(loaded_seg_nifti == seg_id, global_label_id, loaded_seg_nifti)
            seg_id = global_label_id
        else:
            print(f"# Same label-id -> ok")

        print("# Merging...")
        result_overlapping, overlapping_indices = check_overlapping(gt_map=new_gt_map, new_map=loaded_seg_nifti)
        if result_overlapping:
            existing_overlapping_labels = np.unique(new_gt_map[overlapping_indices])
            print("#")
            print("##################################################")
            print("#")
            print(f"# Found overlapping segmentation:")
            for existing_overlapping_label_int in existing_overlapping_labels:
                existing_overlapping_label = [k for k, v in global_labels_info.items() if v == existing_overlapping_label_int][0]
                print("#")
                print(f"# Base_image: {basename(base_image_path)}")
                print(f"# existing vs new: {existing_overlapping_label} vs {extracted_label_tag}")
                print("#")
            print("##################################################")
            print("#")
            if new_global_id:
                del global_labels_info[extracted_label_tag]
            if not fail_if_overlapping and skipping_level == "segmentation":
                print(f"# Skipping this segmentation file!")
                skipped_dict["segmentation_files"].append(seg_nifti)
                continue
            else:
                return queue_dict, "overlapping"

        local_labels_info[seg_id] = extracted_label_tag
        new_gt_map = np.maximum(new_gt_map, loaded_seg_nifti)
        local_gt_map_labels = list(np.unique(new_gt_map))

    print("# Writing new merged file...")
    if int(np.amax(new_gt_map)) == 0:
        print("#")
        print("#")
        print("##################################################")
        print("#")
        print(f"#### No label found in new-label-map !")
        print("# -> skipping")
        print("##################################################")
        print("#")
        print("#")
        if new_global_id:
            del global_labels_info[extracted_label_tag]
        return queue_dict, "no labels found"

    if multi:
        print(f"# Copy base image: {base_image_path}")
        target_dir = join(dirname(dirname(target_dir)), basename(base_image_path).replace(".nii.gz", "_merged"), basename(target_dir))
        target_path_base_image = join(dirname(target_dir), "/".join(base_image_path.split("/")[-2:]))
        Path(dirname(target_path_base_image)).mkdir(parents=True, exist_ok=True)
        shutil.copy2(src=base_image_path, dst=target_path_base_image)

    Path(target_dir).mkdir(parents=True, exist_ok=True)
    merged_counter += 1
    metadata_json = create_metadata_json(local_labels_info)
    metadata_json_path = join(target_dir, "metadata.json")
    with open(metadata_json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata_json, f, indent=4, sort_keys=False)
    target_path_merged = join(target_dir, "merged_segs.nii.gz")
    combined = nib.Nifti1Image(new_gt_map, example_img.affine, example_img.header)
    combined.to_filename(target_path_merged)
    print("# Checking if resampling is needed...")
    base_img_shape = base_image_loaded.shape
    merged_nifti_shape = nib.load(target_path_merged).shape
    if base_img_shape != merged_nifti_shape:
        print(f"# Staring resampling: {base_img_shape} vs {merged_nifti_shape}")
        resampling_success = resample_image(input_path=target_path_merged, original_path=base_image_path)
        if not resampling_success:
            if new_global_id:
                del global_labels_info[extracted_label_tag]
            return queue_dict, "resampling failed"
        print("# Check if resampling-result...")
        merged_nifti_shape = nib.load(target_path_merged).shape
        if base_img_shape != merged_nifti_shape:
            print("# Resampling was not successful!")
            if new_global_id:
                del global_labels_info[extracted_label_tag]
            return queue_dict, "resampling failed"
        else:
            print("# Resampling successful!")
    else:
        print("# No resampling needed.")

    if delete_merged_data:
        for seg_nifti in seg_nifti_list:
            print(f"# Removing merged NIFTI-file: {seg_nifti}")
            shutil.rmtree(seg_nifti, ignore_errors=True)

    print("# Done")
    return queue_dict, "ok"


def resample_image(input_path, original_path, replace=True, target_dir=None):
    global execution_timeout, executable, interpolator
    print("#")
    print(f"# Resampling:")
    print("#")
    if not replace:
        if target_dir is None:
            print("# Replace == False and target_dir not set!")
            exit(1)
        target_path = join(target_dir, basename(input_path))
    else:
        target_path = input_path

    command = [str(executable), "-f", str(original_path), "-m", str(input_path), "-o", str(target_path), "--interpolator", str(interpolator)]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=execution_timeout)
    # command stdout output -> output.stdout
    # command stderr output -> output.stderr
    if output.returncode != 0:
        print("#")
        print("##################################################")
        print("#")
        print("##################  ERROR  #######################")
        print("#")
        print("# ----> Something went wrong with the shell-execution!")
        print(f"# Command:  {command}")
        print("#")
        print(f"# STDERR: {output.stderr}")
        print("#")
        print("##################################################")
        print("#")
        return False

    return True


workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None

batch_name = getenv("BATCH_NAME", "batch")
batch_name = batch_name if batch_name.lower() != "none" else None
assert batch_name is not None

operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
assert operator_in_dir is not None

org_input_dir = getenv("ORG_IMG_IN_DIR", "None")
org_input_dir = org_input_dir if org_input_dir.lower() != "none" else None
assert org_input_dir is not None

operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
assert operator_out_dir is not None

executable = getenv("EXECUTABLE", "/src/MitkCLResampleImageToReference.sh")
executable = executable if executable.lower() != "none" else None
assert executable is not None

# 0=linear (default), 1=nearest neighbor, 2=sinc (optional), (default: 0), Type: Int
interpolator = getenv("INTERPOLATOR", "None")
interpolator = int(interpolator) if interpolator.lower() != "none" else 1

input_file_extension = getenv("INPUT_FILE_EXTENSION", "*.nii.gz")
input_file_extension = input_file_extension if input_file_extension.lower() != "none" else None
assert input_file_extension is not None

parallel_processes = getenv("THREADS", "1")
parallel_processes = int(parallel_processes) if parallel_processes.lower() != "none" else None
assert parallel_processes is not None

fail_if_overlapping = getenv("FAIL_IF_OVERLAPPING", "None")
fail_if_overlapping = True if fail_if_overlapping.lower() == "true" else False

fail_if_label_already_present = getenv("FAIL_IF_LABEL_ALREADY_PRESENT", "None")
fail_if_label_already_present = False if fail_if_label_already_present.lower() == "false" else True

fail_if_label_not_extractable = getenv("FAIL_IF_LABEL_ALREADY_PRESENT", "None")
fail_if_label_not_extractable = False if fail_if_label_not_extractable.lower() == "false" else True

force_same_labels = getenv("FORCE_SAME_LABELS", "None")
force_same_labels = True if force_same_labels.lower() == "true" else False

delete_merged_data = getenv("DELETE_MERGED_DATA", "None")
delete_merged_data = False if delete_merged_data.lower() == "false" else True

# workflow_dir = "/home/jonas/Downloads/new_data"
# batch_name = "batch"
# operator_in_dir = "dcmseg2nrrd-seg"
# org_input_dir = "dcm-converter-ct"
# operator_out_dir = "output_seg_check"
# executable = "/home/jonas/software/mitk-phenotyping/MitkCLResampleImageToReference.sh"
# fail_if_overlapping = False
# parallel_processes = 3
# delete_merged_data = False

skipping_level = "base_image"  # or 'segmentation'

print("##################################################")
print("#")
print("# Starting resampling:")
print("#")
print(f"# workflow_dir:     {workflow_dir}")
print(f"# batch_name:       {batch_name}")
print(f"# org_input_dir:    {org_input_dir}")
print(f"# operator_in_dir:  {operator_in_dir}")
print(f"# operator_out_dir: {operator_out_dir}")
print("#")
print(f"# force_same_labels: {force_same_labels}")
print(f"# delete_merged_data: {delete_merged_data}")
print(f"# fail_if_overlapping: {fail_if_overlapping}")
print(f"# fail_if_label_already_present: {fail_if_label_already_present}")
print(f"# fail_if_label_not_extractable: {fail_if_label_not_extractable}")
print("#")
print("##################################################")
print("#")
print("# Starting processing on BATCH-ELEMENT-level ...")
print("#")
print("##################################################")
print("#")

base_image_ref_dict = {}
global_labels_info = {}

# Loop for every batch-element (usually series)
batch_dir_path = join('/', workflow_dir, batch_name)
batch_folders = [f for f in glob(join(batch_dir_path, '*'))]
for batch_element_dir in batch_folders:
    print("####################################################################################################")
    print("#")
    print(f"# Processing batch-element:")
    print(f"# {batch_element_dir}")
    print("#")
    print("####################################################################################################")
    print("#")
    element_output_dir = join(batch_element_dir, operator_out_dir)
    base_input_dir = join(batch_element_dir, org_input_dir)
    seg_input_dir = join(batch_element_dir, operator_in_dir)

    base_files = sorted(glob(join(base_input_dir, "*.nii*"), recursive=False))
    assert len(base_files) == 1
    seg_files = sorted(glob(join(seg_input_dir, "*.nii*"), recursive=False))
    if len(seg_files) == 0:
        print("#")
        print("####################################################################################################")
        print("#")
        print(f"# No segmentation NIFTI found -> skipping")
        print("#")
        print("####################################################################################################")
        print("#")
        continue

    base_file = base_files[0]
    base_series_id = basename(base_file)
    if base_series_id not in base_image_ref_dict:
        base_image_ref_dict[base_series_id] = {
            "base_file": base_file,
            "output_dir": element_output_dir,
            "batch_elements": {}
        }

    if len(seg_files) == 0:
        print("here")
    if batch_element_dir not in base_image_ref_dict[base_series_id]["batch_elements"]:
        base_image_ref_dict[base_series_id]["batch_elements"][batch_element_dir] = {
            "file_count": 0,
            "seg_files": []
        }

    for seg_file in seg_files:
        if seg_file not in base_image_ref_dict[base_series_id]["batch_elements"][batch_element_dir]:
            base_image_ref_dict[base_series_id]["batch_elements"][batch_element_dir]["seg_files"].append(seg_file)
            base_image_ref_dict[base_series_id]["batch_elements"][batch_element_dir]["file_count"] += 1

    batch_elements_sorted = {}
    for batch_element_dir in sorted(base_image_ref_dict[base_series_id]["batch_elements"], key=lambda batch_element_dir: base_image_ref_dict[base_series_id]["batch_elements"][batch_element_dir]["file_count"], reverse=True):
        batch_elements_sorted[batch_element_dir] = base_image_ref_dict[base_series_id]["batch_elements"][batch_element_dir]

    base_image_ref_dict[base_series_id]["batch_elements"] = batch_elements_sorted

queue_dicts = []
for key in sorted(base_image_ref_dict.keys(), key=lambda key: base_image_ref_dict[key]['batch_elements'][list(base_image_ref_dict[key]['batch_elements'].keys())[0]]["file_count"], reverse=True):
    value = base_image_ref_dict[key]
    base_image = value["base_file"]
    batch_elements_with_files = value["batch_elements"]
    print(f"# Base image: {base_image}")

    multi = False
    target_dir = value["output_dir"]
    if len(batch_elements_with_files.keys()) == 1:
        print("# Single batch-element segmentations!")
    elif len(batch_elements_with_files.keys()) > 1:
        print("# Multi batch-element segmentations!")
        multi = True
    else:
        print("# unknown list!")
        exit(1)

    segs_to_merge = {
        "base_image": base_image,
        "target_dir": target_dir,
        "multi": multi,
        "seg_files": [],
        "batch_elements_to_remove": [],
    }
    for batch_element_with_files, info_dict in batch_elements_with_files.items():
        if multi:
            segs_to_merge["batch_elements_to_remove"].append(batch_element_with_files)

        for seg_element_file in sorted(info_dict["seg_files"], key=lambda seg_element_file: (seg_element_file.split("/")[-3], int(seg_element_file.split("--")[-2])), reverse=False):
            segs_to_merge["seg_files"].append(seg_element_file)

        # for seg_element_file in info_dict["seg_files"]:
    queue_dicts.append(segs_to_merge)

print("#")
print("# Staring merging ...")
print("#")
nifti_results = ThreadPool(parallel_processes).imap_unordered(merge_niftis, queue_dicts)
for queue_dict, nifti_result in nifti_results:
    target_dir = queue_dict["target_dir"]
    seg_nifti_list = queue_dict["seg_files"]
    base_image = queue_dict["base_image"]
    batch_elements_to_remove = queue_dict["batch_elements_to_remove"]

    remove_elements = False

    print(f"# Result for {base_image} arrived: {nifti_result}")
    if nifti_result == "ok":
        processed_count += 1
        remove_elements = True
    elif nifti_result == "overlapping":
        if fail_if_overlapping:
            exit(1)
        elif skipping_level == "base_image":
            print(f"# Skipping overlapping segmentations -> deleting batch-elements for gt-image: {base_image}")
            skipped_dict["base_images"].append(base_image)
            remove_elements = True
        else:
            print(f"# Should not happen...")
            exit(1)

    elif nifti_result == "extracted_label_tag is None":
        if fail_if_label_not_extractable:
            exit(1)
    elif nifti_result == "seg_id is None":
        exit(1)
    elif nifti_result == "resampling failed":
        exit(1)
    elif nifti_result == "no labels found":
        exit(1)
    else:
        print(f"# Unknown status message: {nifti_result}")
        exit(1)
    if remove_elements:
        for batch_element_to_remove in batch_elements_to_remove:
            print(f"# Removing merged dir: {batch_element_to_remove}")
            shutil.rmtree(batch_element_to_remove, ignore_errors=True)


if len(skipped_dict["base_images"]) > 0 or len(skipped_dict["segmentations"]) > 0:
    print("##################################################")
    print("# ")
    print("# Skipped elements: ")
    print("# ")
    print(json.dumps(skipped_dict, indent=4, sort_keys=True, default=str))
    print("# ")
    print("#")
    print("##################################################")

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
