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
from pydicom.uid import generate_uid

# For multiprocessing
from multiprocessing.pool import ThreadPool

# For shell-execution
from subprocess import PIPE, run

execution_timeout = 120

# Counter to check if smth has been processed
global_labels_info_count = {}

processed_count = 0
merged_counter = 0
label_encoding_counter = 0

base_image_ref_dict = {}
skipped_dict = {
    "segmentation_files": [],
    "base_images": []
}


def write_global_seg_info(file_path):
    global global_labels_info
    with open(file_path, "w", encoding='utf-8') as jsonData:
        json.dump(global_labels_info, jsonData, indent=4, ensure_ascii=True)


def read_global_seg_info():
    global global_labels_info_path, global_labels_info
    if not exists(global_labels_info_path):
        global_labels_info = {}
        write_global_seg_info(file_path=global_labels_info_path)

    with open(global_labels_info_path, "r") as f:
        global_labels_info = json.load(f)


def check_transformations(current_config):
    global global_labels_info_count, global_labels_info, target_dict_dir, label_encoding_counter

    transformations = {}
    for label_key, int_encoding in current_config.items():
        int_encoding = int(int_encoding)
        if label_key not in global_labels_info:
            if target_dict_dir is not None:
                print(f"#")
                print(f"# target_dict_dir exists")
                print(f"#")
                print(f"# Label {label_key} was found in current_config -> but not in global_labels_info!")
                print(f"# Needed tranformation: int_encoding {int_encoding} -> ✘ delete")
                print(f"#")
                transformations[int_encoding] = {
                    "kind": "delete"
                }
            else:
                print(f"#")
                print(f"# Label {label_key} was found in current_config -> but not in global_labels_info!")
                label_encoding_counter += 1
                print(f"# -> added label_int {label_encoding_counter} to global_labels_info")
                global_labels_info[label_key] = label_encoding_counter
                global_labels_info_count[label_key] = 1
                write_global_seg_info(file_path=global_labels_info_path)
                # existing_labels_with_encoding = list(global_labels_info.keys())[list(global_labels_info.values()).index(int_encoding)]
                if label_encoding_counter == int_encoding:
                    print(f"# No transformation needed.")
                    print(f"#")
                else:
                    print(f"# New encoding needed: {int_encoding} -> switching to {label_encoding_counter}")
                    transformations[int_encoding] = {
                        "kind": "change",
                        "label_name": label_key,
                        "new_encoding": label_encoding_counter
                    }
                    continue

        else:
            should_int_encoding = int(global_labels_info[label_key])
            if label_key not in global_labels_info_count:
                global_labels_info_count[label_key] = 1
            else:
                global_labels_info_count[label_key] += 1

            if int_encoding != should_int_encoding:
                print(f"#")
                print(f"# current: {label_key} : {int_encoding}")
                print(f"# target:  {label_key} : {should_int_encoding}")
                print(f"# Needed tranformation: task_target {int_encoding} -> {should_int_encoding}")
                print(f"#")
                transformations[int_encoding] = {
                    "kind": "change",
                    "label_name": label_key,
                    "new_encoding": should_int_encoding
                }
                continue
            else:
                print(f"#")
                print(f"# ✓ {label_key}: current {int_encoding} == global {should_int_encoding}")
                print(f"#")

    return transformations


def create_metadata_json(new_labels_dict):
    if "Clear Label" not in new_labels_dict:
        new_labels_dict["Clear Label"] = 0

    metadata_dict = {
        "segmentAttributes": []
    }

    for label_key, int_encoding in new_labels_dict.items():
        metadata_dict["segmentAttributes"].append(
            [{
                "SegmentLabel": str(label_key),
                "TrackingIdentifier": str(label_key),
                "labelID": int(int_encoding),
            }]
        )

    return metadata_dict


def check_overlap(gt_map, new_map, seg_nifti):
    global skipped_dict, max_overlap_percentage

    gt_map = np.where(gt_map != 0, 1, gt_map)
    new_map = np.where(new_map != 0, 1, new_map)

    agg_arr = gt_map + new_map
    max_value = int(np.amax(agg_arr))
    if max_value > 1:
        print("#")
        print("##################################################")
        print("#")
        print("# overlap Segmentations!!!")
        print("#")
        print(f"# NIFTI: {seg_nifti}")
        print("#")
        overlap_indices = agg_arr > 1
        overlap_voxel_count = overlap_indices.sum()
        overlap_percentage = 100 * float(overlap_voxel_count)/float(gt_map.size)

        print(f"# overlap_percentage: {overlap_percentage} / {max_overlap_percentage}")
        if overlap_percentage > max_overlap_percentage:
            print("# Too many voxels are overlap -> skipping")
            print("#")
            print(f"# overlap_percentage: {overlap_percentage:.6f} > max_overlap_percentage: {max_overlap_percentage}")
            print("##################################################")
            print("#")
            skipped_dict["segmentation_files"].append(f"-> removed: {basename(seg_nifti)}: {overlap_percentage:.6f}% / {max_overlap_percentage}% overlap")
            return True, overlap_indices, overlap_percentage
        else:
            print("# Not enough voxels are overlap -> ok")
            print("#")
            print("##################################################")
            print("#")
            skipped_dict["segmentation_files"].append(f"-> still ok: {basename(seg_nifti)}: {overlap_percentage:.6f}% / {max_overlap_percentage}% overlap")
            return False, None, None
    else:
        return False, None, None


def merge_niftis(queue_dict):
    global merge_all_niftis, one_hot_format, global_labels_info, global_labels_info_count, merged_counter, delete_merged_data, fail_if_overlap, skipping_level

    target_dir = queue_dict["target_dir"]
    base_image_path = queue_dict["base_image"]
    seg_nifti_list = queue_dict["seg_files"]
    multi = queue_dict["multi"]

    base_image_loaded = nib.load(base_image_path)
    base_image_dimensions = base_image_loaded.shape
    new_gt_map = np.zeros_like(base_image_loaded.get_fdata().astype(int))
    new_gt_map_int_encodings = list(np.unique(new_gt_map))
    
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
        if not merge_all_niftis:
            new_gt_map = np.zeros_like(base_image_loaded.get_fdata().astype(int))
            local_labels_info = {}
        print(f"# Processing NIFTI: {basename(seg_nifti)}")
        print("#")
        existing_configuration = None
        print("#")

        meta_info_json_path = glob(join(dirname(seg_nifti), "*.json"), recursive=False)
        if len(meta_info_json_path) == 1 and exists(meta_info_json_path[0]):
            existing_configuration = {}
            meta_info_json_path = meta_info_json_path[0]
            if "seg_info.json" in meta_info_json_path:
                print(f"# Found nnunet meta-json: {meta_info_json_path}")
                with open(meta_info_json_path, 'rb') as f:
                    meta_info = json.load(f)

                if "seg_info" in meta_info:
                    for label_entry in meta_info["seg_info"]:
                        label_int = label_entry["label_int"]
                        label_name = label_entry["label_name"]
                        existing_configuration[label_name] = str(label_int)

            elif "-meta.json" in meta_info_json_path:
                print(f"# Found DCMQI meta-json: {meta_info_json_path}")
                assert "--" in seg_nifti
                seg_file_info = seg_nifti.split("--")
                seg_id = seg_file_info[-2]
                label_int = None
                label_name = None
                existing_configuration = {}
                with open(meta_info_json_path, 'rb') as f:
                    meta_info = json.load(f)

                if "segmentAttributes" in meta_info:
                    for entries in meta_info["segmentAttributes"]:
                        for part in entries:
                            if "labelID" in part and str(part["labelID"]) == seg_id:
                                label_int = int(part["labelID"])
                                print(f"# label_int: {label_int}")
                            if "SegmentLabel" in part:
                                label_name = part["SegmentLabel"]

                            elif "TrackingIdentifier" in part:
                                label_name = part["TrackingIdentifier"]

                if label_int is None or label_name is None:
                    return queue_dict, "label extraction issue"
                existing_configuration[label_name] = str(label_int)

        if existing_configuration is None:
            return queue_dict, "label extraction issue"

        print(f"# Loading NIFTI: {seg_nifti}")
        loaded_nib_nifti = nib.load(seg_nifti)
        if base_image_dimensions != loaded_nib_nifti.shape:
            print("# Issue with different dimensions in seg-NIFTIS!")
            print("# -> starting resampling..")
            resampling_success = resample_image(input_path=seg_nifti, original_path=base_image_path)
            if not resampling_success:
                return queue_dict, "resampling failed"
            print("# -> checking dimensions ...")
            loaded_nib_nifti = nib.load(seg_nifti)
            assert base_image_dimensions == loaded_nib_nifti.shape
            print("# -> dimensions ok")
        else:
            print("# No resampling needed.")

        print(f"#")
        transformations = check_transformations(current_config=existing_configuration)
        if len(transformations) == 0:
            print(f"# No transformations needed!")
            print(f"# -> check if single file ...")
            if len(seg_nifti_list) == 1:
                print(f"# -> file ok")
                target_path = join(target_dir,basename(seg_nifti))
                if target_path != seg_nifti:
                    print(f"# -> copy file to target: {target_path}")
                    Path(dirname(target_path)).mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src=base_image_path, dst=target_path)

                local_labels_info[label_name] = str(seg_id)
                metadata_json = create_metadata_json(new_labels_dict=local_labels_info)
                metadata_json_path = join(target_dir, "metadata.json")
                with open(metadata_json_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata_json, f, indent=4, sort_keys=False)
                return queue_dict, "ok"
            else:
                print("# -> merging multiple files -> continue")
                print("#")

        loaded_seg_nifti_numpy = loaded_nib_nifti.get_fdata().astype(int)
        print("#")
        nifti_int_encodings = list(np.unique(loaded_seg_nifti_numpy))
        if len(nifti_int_encodings) == 1:
            print("##################################################### ")
            print("#")
            print("# No segmentation was found in result-NIFTI-file!")
            print(f"# NIFTI-file {seg_nifti}")
            print("#")
            print("##################################################### ")
            continue

        for int_encoding in nifti_int_encodings:
            int_encoding = int(int_encoding)
            print(f"# Loading encoding {int_encoding}")
            if int_encoding == 0:
                print(f"# Clear Label -> continue")
                continue

            # loaded_seg_nifti_label = loaded_seg_nifti_numpy
            # loaded_seg_nifti_label = np.array(loaded_seg_nifti_numpy)
            loaded_seg_nifti_label = np.where(loaded_seg_nifti_numpy != int_encoding, 0, loaded_seg_nifti_numpy)
            label_found = list(existing_configuration.keys())[list(existing_configuration.values()).index(str(int_encoding))]

            if len(transformations) > 0 and int_encoding in transformations:
                print(f"# label_bin: {int_encoding} -> transformation needed")
                transformation = transformations[int_encoding]
                kind = transformation["kind"]
                if kind == "change":
                    new_encoding = int(transformation["new_encoding"])
                    print(f"# change {label_found}: {int_encoding} -> {new_encoding}")
                    loaded_seg_nifti_label = np.where(loaded_seg_nifti_label == int_encoding, new_encoding, loaded_seg_nifti_label)
                    int_encoding = new_encoding

                if kind == "delete":
                    print(f"# delete {label_found}: {int_encoding} -> 0")
                    # loaded_seg_nifti_label = np.where(loaded_seg_nifti_label == int_encoding, 0, loaded_seg_nifti_label)
                    continue

            if label_found not in local_labels_info:
                local_labels_info[label_found] = int_encoding
            else:
                print(f"# Label already found in local_labels_info")
                print(f"# label_found: {label_found} - int_encoding: {int_encoding}")
                print(f"# vs")
                print(f"# local_labels_info[{label_found}]: {local_labels_info[label_found]}")
                assert str(local_labels_info[label_found]) == int_encoding

            print("# Check overlap ...")
            result_overlap, overlap_indices, overlap_percentage = check_overlap(gt_map=new_gt_map, new_map=loaded_seg_nifti_label, seg_nifti=seg_nifti)
            if result_overlap:
                existing_overlap_labels = np.unique(new_gt_map[overlap_indices])
                print("#")
                print("##################################################")
                print("#")
                print(f"# Found overlap segmentation:")
                for existing_overlap_label_int in existing_overlap_labels:
                    existing_overlap_label = [k for k, v in global_labels_info.items() if v == existing_overlap_label_int]
                    if len(existing_overlap_label) > 0:
                        existing_overlap_label = existing_overlap_label[0]
                    else:
                        print(f"# Could not find any existing_overlap_label for encoding: {existing_overlap_label_int}")
                        existing_overlap_label = "Not found!"
                    print("#")
                    print(f"# Base_image: {basename(base_image_path)}")
                    print(f"# existing vs new: {existing_overlap_label} vs {label_found}")
                    print("#")
                print("##################################################")
                print("#")

                global_labels_info_count[label_found] -= 1
                if global_labels_info_count[label_found] <= 0:
                    del global_labels_info_count[label_found]
                    del global_labels_info[label_found]

                if not fail_if_overlap and skipping_level == "segmentation":
                    print(f"# Skipping this segmentation seg!")
                    continue
                else:
                    return queue_dict, "overlap"
            print("#")
            print("# -> no overlap ♥")
            print("#")
            print(f"# Merging new_gt_map + loaded_seg_nifti_label: {int_encoding}")
            print("#")
            # print(f"# Old labels: {new_gt_map_int_encodings}")
            new_gt_map = np.maximum(new_gt_map, loaded_seg_nifti_label)
            # print(f"# Merging done.")
            # new_gt_map_int_encodings = list(np.unique(new_gt_map))
            # print(f"# New labels: {new_gt_map_int_encodings}")


        if not merge_all_niftis:
            print("# No NIFTI merge -> replacing original NIFTI")
            print(f"# Path: {seg_nifti}")
            combined = nib.Nifti1Image(new_gt_map, base_image_loaded.affine, base_image_loaded.header)
            combined.to_filename(seg_nifti)
            write_global_seg_info(file_path=meta_info_json_path)

    if merge_all_niftis:
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
        target_path_merged = join(target_dir, f"{generate_uid()}_merged.nii.gz")
        combined = nib.Nifti1Image(new_gt_map, base_image_loaded.affine, base_image_loaded.header)
        combined.to_filename(target_path_merged)
        print("# Checking if resampling is needed...")
        merged_nifti_shape = nib.load(target_path_merged).shape
        if base_image_dimensions != merged_nifti_shape:
            print(f"# Staring resampling: {base_image_dimensions} vs {merged_nifti_shape}")
            resampling_success = resample_image(input_path=target_path_merged, original_path=base_image_path)
            if not resampling_success:
                return queue_dict, "resampling failed"
            print("# Check if resampling-result...")
            merged_nifti_shape = nib.load(target_path_merged).shape
            if base_image_dimensions != merged_nifti_shape:
                print("# ✘ Resampling was not successful!")
                return queue_dict, "resampling failed"
            else:
                print("# ✓  Resampling successful!")
        else:
            print("# No resampling needed.")

        if delete_merged_data:
            for seg_nifti in seg_nifti_list:
                print(f"# Removing merged NIFTI-file: {seg_nifti}")
                shutil.rmtree(seg_nifti, ignore_errors=True)

    print("# Done")
    write_global_seg_info(file_path=global_labels_info_path)
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

# os.environ['WORKFLOW_DIR'] = str("/home/jonas/Downloads/dice_test_data/nnunet-ensemble-210506211134235449")

# os.environ['WORKFLOW_DIR'] = str("/home/jonas/Downloads/dice_test_data/nnunet-ensemble-210506104227376005")
# os.environ['ORG_IMG_IN_DIR'] = str("dcm-converter-ct")
# os.environ['OPERATOR_IN_DIR'] = str("dcmseg2nrrd-gt")
# os.environ['OPERATOR_OUT_DIR'] = str("seg-check")
# os.environ['EXECUTABLE'] = str("/home/jonas/software/mitk-phenotyping/MitkCLResampleImageToReference.sh")
# os.environ['BATCH_NAME'] = str("nnunet-cohort")

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

fail_if_overlap = getenv("FAIL_IF_overlap", "None")
fail_if_overlap = True if fail_if_overlap.lower() == "true" else False

fail_if_label_already_present = getenv("FAIL_IF_LABEL_ALREADY_PRESENT", "None")
fail_if_label_already_present = False if fail_if_label_already_present.lower() == "false" else True

fail_if_empty_gt = getenv("FAIL_IF_EMPTY_GT", "None")
fail_if_empty_gt = True if fail_if_empty_gt.lower() == "true" else False

fail_if_label_not_extractable = getenv("FAIL_IF_LABEL_ALREADY_PRESENT", "None")
fail_if_label_not_extractable = False if fail_if_label_not_extractable.lower() == "false" else True

force_same_labels = getenv("FORCE_SAME_LABELS", "None")
force_same_labels = True if force_same_labels.lower() == "true" else False

delete_merged_data = getenv("DELETE_MERGED_DATA", "None")
delete_merged_data = False if delete_merged_data.lower() == "false" else True

target_dict_dir = getenv("TARGET_DICT_DIR", "None")
target_dict_dir = target_dict_dir if target_dict_dir.lower() != "none" else None

max_overlap_percentage = getenv("MAX_overlap", "0.001")
max_overlap_percentage = float(max_overlap_percentage) if max_overlap_percentage.lower() != "none" else None

merge_all_niftis = True
one_hot_format = False

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
print(f"# fail_if_overlap: {fail_if_overlap}")
print(f"# fail_if_label_already_present: {fail_if_label_already_present}")
print(f"# fail_if_label_not_extractable: {fail_if_label_not_extractable}")
print("#")
print(f"# parallel_processes: {parallel_processes}")
print("#")
print("##################################################")
print("#")
print("# Starting processing on BATCH-ELEMENT-level ...")
print("#")
print("##################################################")
print("#")

if target_dict_dir is not None:
    global_labels_info_path = join('/', workflow_dir, target_dict_dir, "global_seg_info.json")
else:
    global_labels_info_path = join('/', workflow_dir, operator_out_dir, "global_seg_info.json")
print("#")
print("##################################################")
print("#")
print(f"# global_labels_info_path: {global_labels_info_path}")
print("#")
print("##################################################")
print("#")
Path(dirname(global_labels_info_path)).mkdir(parents=True, exist_ok=True)
read_global_seg_info()

batch_dir_path = join('/', workflow_dir, batch_name)
# Loop for every batch-element (usually series)
batch_folders = [f for f in glob(join(batch_dir_path, '*'))]
for batch_element_dir in batch_folders:
    element_output_dir = join(batch_element_dir, operator_out_dir)
    base_input_dir = join(batch_element_dir, org_input_dir)
    seg_input_dir = join(batch_element_dir, operator_in_dir)

    print(f"# Searching for base_images @ {base_input_dir}")
    base_files = sorted(glob(join(base_input_dir, "*.nii*"), recursive=False))
    print(f"# Found {len(base_files)}")
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
        if "--" not in info_dict["seg_files"][0]:
            for seg_element_file in sorted(info_dict["seg_files"], reverse=False):
                segs_to_merge["seg_files"].append(seg_element_file)
        else:
            for seg_element_file in sorted(info_dict["seg_files"], key=lambda seg_element_file: (seg_element_file.split("/")[-3], int(seg_element_file.split("--")[-2])), reverse=False):
                segs_to_merge["seg_files"].append(seg_element_file)

        # for seg_element_file in info_dict["seg_files"]:
    queue_dicts.append(segs_to_merge)

print("#")
print("# Staring merging ...")
print("#")
nifti_results = ThreadPool(parallel_processes).imap_unordered(merge_niftis, queue_dicts)
for queue_dict, nifti_result in nifti_results:
    processed_count += 1
    target_dir = queue_dict["target_dir"]
    seg_nifti_list = queue_dict["seg_files"]
    base_image = queue_dict["base_image"]
    batch_elements_to_remove = queue_dict["batch_elements_to_remove"]

    remove_elements = False
    print("#")
    print("# ")
    print("####################################################################################################")
    print("#")
    print(f"# Result for {base_image} arrived: {nifti_result}")
    print("#")
    print(f"# ----> process_count: {processed_count}/{len(queue_dicts)}")
    print("#")
    print("####################################################################################################")
    print("# ")
    print("# ")
    if nifti_result == "ok":
        remove_elements = True
    elif nifti_result == "overlap":
        if fail_if_overlap:
            exit(1)
        elif skipping_level == "base_image":
            print(f"# Skipping overlap segmentations -> deleting batch-elements for gt-image: {base_image}")
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
    elif nifti_result == "label extraction issue":
        exit(1)
    elif nifti_result == "no labels found":
        print("##################################################")
        print("# ")
        print("# No labels could be found in merged-gt-mask! ")
        print(f"# {base_image}")
        print("# ")
        if fail_if_empty_gt:
            exit(1)
        else:
            remove_elements = True
            print("# Skipping -> deleting batch-elements for gt-image: ")
            print("#")
            print("##################################################")
    else:
        print(f"# Unknown status message: {nifti_result}")
        exit(1)
    if remove_elements:
        for batch_element_to_remove in batch_elements_to_remove:
            print(f"# Removing merged dir: {batch_element_to_remove}")
            shutil.rmtree(batch_element_to_remove, ignore_errors=True)


if len(skipped_dict["base_images"]) > 0 or len(skipped_dict["segmentation_files"]) > 0:
    print("##################################################")
    print("# ")
    print("# Overlap elements: ")
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
    write_global_seg_info(file_path=global_labels_info_path)
    print("# DONE #")
