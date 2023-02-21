from genericpath import isdir
import os
import glob
import json
import shutil
from pathlib import Path
import random
import time
import nibabel as nib
import numpy as np
from multiprocessing.pool import ThreadPool
from os.path import join, exists, dirname, basename, isdir


def timing(f):
    def wrap(*args, **kwargs):
        time1 = time.time()
        ret = f(*args, **kwargs)
        time2 = time.time()
        print('{:s} function took {:.3f} s'.format(f.__name__, (time2-time1)))
        return ret
    return wrap


def check_if_encoding_in_use(label_encoding):
    global label_names_found
    found = False
    next_free_label = None

    existing_label_encodings = list(label_names_found.values())
    if label_encoding in existing_label_encodings:
        for i in range(1, 100):
            # for i in range(max(existing_label_encodings), 100):
            if i not in list(label_names_found.values()):
                next_free_label = i
                break

        assert next_free_label is not None
        print("#")
        print("###################################### WARNING ###################################### ")
        print("#")
        print(f"# Label encoding '{label_encoding}' has already been used for a different label!!")
        print(f"# -> switching to next free label: {label_encoding} -> {next_free_label}")
        print("#")
        print("##################################################################################### ")
        print("#")
        label_encoding = next_free_label

    return label_encoding


def process_seg_nifti(seg_nifti):
    global label_names_found, global_label_index

    label_tag = "N/A"
    seg_id = None
    extracted_label_tag = None
    print("#")
    print(f"# Processing NIFTI: {seg_nifti}")
    print("#")
    if "--" in seg_nifti:
        seg_info = seg_nifti.split("--")
        extracted_label_tag = seg_info[-1].split(".")[0].replace("_", " ").replace("++", "/")
        seg_id = seg_info[1]

    meta_info_json_path = glob.glob(join(dirname(seg_nifti), "*.json"), recursive=False)
    if len(meta_info_json_path) == 1 and exists(meta_info_json_path[0]):
        meta_info_json_path = meta_info_json_path[0]
        print("# Found DCMQI meta-json")
        with open(meta_info_json_path, 'r') as f:
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
    if seg_id is None:
        print("#")
        print("#")
        print("####### Could not extract label seg_id from file!")
        print("#")
        print("#")
        return None, None

    if extracted_label_tag is None:
        print("#")
        print("#")
        print("####### Could not extract label encoding from file!")
        print("#")
        print("#")
        return None, None

    print(f"# Extracted label: {extracted_label_tag}")
    label_tag = extracted_label_tag
    # your code here
    nii_array = nib.load(seg_nifti).get_data().astype(int)
    nifti_labels = list(np.unique(nii_array))
    if 0 in nifti_labels:
        nifti_labels.remove(0)
    else:
        print("#")
        print(f"# Couldn't find a 'Clear Label' 0 in NIFTI: {seg_nifti}")
        print("#")
        return None, None

    if len(nifti_labels) != 1:
        print("#")
        print(f"# More than one label found in NIFTI: {seg_nifti}")
        print(f"# Single label segmentation NIFTIs expected -> error")
        print("# ")
        return None, None

    nifti_bin_encoding = nifti_labels[0]
    if label_tag not in label_names_found:
        print(f"# Adding label: {label_tag} ...")
        if use_nifti_labels:
            label_int = nifti_bin_encoding
            print(f"# -> using NIFTI encoding: {label_int}")
        else:
            global_label_index += 1
            label_int = global_label_index
            print(f"# -> using default encoding: {label_int}")

        label_int = check_if_encoding_in_use(label_int)

        if label_int != nifti_bin_encoding:
            print(f"# replacing labels: {label_tag} -> from {nifti_bin_encoding} -> to {label_int}")
            nii_array = np.where(nii_array == nifti_bin_encoding, label_int, nii_array)
            nifti_bin_encoding = label_int

        label_names_found[label_tag] = label_int
    else:
        print(f"# Label {label_tag} already present -> checking NIFTI encoding...")
        if label_names_found[label_tag] != nifti_bin_encoding:
            if use_nifti_labels:
                print("#")
                print("###################### WARNING ###################### ")
                print("#")
                print(f"# Label '{label_tag}' has already been found but the integer encoding differs to the NIFTI !")
                print(f"# New NIFTI encoding:  {nifti_bin_encoding}")
                print(f"# Existing encoding:   {label_names_found[label_tag] }")
                print("#")
                print(f"# replacing labels: {label_tag} -> from {nifti_bin_encoding} -> to {label_names_found[label_tag]}")
                print("#")
                print("##################################################### ")
                print("#")
            else:
                print(f"# replacing labels: {label_tag} -> from {nifti_bin_encoding} -> to {label_names_found[label_tag]}")
            nii_array = np.where(nii_array == nifti_bin_encoding, label_names_found[label_tag], nii_array)
            nifti_bin_encoding = label_names_found[label_tag]
        else:
            print("# NIFTI encoding -> ok")

    return nii_array, seg_nifti


def prepare_dataset(datset_list, dataset_id):
    global template_dataset_json, label_names_found, thread_count
    print(f"# Preparing all {dataset_id} series: {len(datset_list)}")
    for series in datset_list:
        print("######################################################################")
        print("#")
        print("# Processing series:")
        print(f"# {series}")
        print("#")
        print("######################################################################")

        imagesTr_path = join(task_dir, "imagesTr")
        base_file_path = f"{basename(series)}.nii.gz"

        for i in range(0, len(input_modality_dirs)):
            modality_nifti_dir = join(series, input_modality_dirs[i])
            modality_nifti = glob.glob(join(modality_nifti_dir, "*.nii.gz"), recursive=True)
            if len(modality_nifti) != 1:
                print("# ")
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("# ")
                print("# Error with training image-file!")
                print("# Found {} files at: {}".format(len(modality_nifti), modality_nifti_dir))
                print("# Expected exactly one file! -> abort.")
                print("# ")
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("# ")
                exit(1)
            modality_nifti = modality_nifti[0]
            target_modality_path = join(imagesTr_path, base_file_path.replace(".nii.gz", f"_{i:04}.nii.gz"))
            Path(dirname(target_modality_path)).mkdir(parents=True, exist_ok=True)
            if copy_target_data:
                shutil.copy2(modality_nifti, target_modality_path)
            else:
                shutil.move(modality_nifti, target_modality_path)

        target_seg_path = join(task_dir, "labelsTr", base_file_path)

        seg_nifti_list = []
        for label_dir in input_label_dirs:
            seg_niftis = glob.glob(join(series, label_dir, "*.nii.gz"), recursive=True)
            seg_nifti_list.extend(seg_niftis)

        print(f"# Found {len(seg_nifti_list)} seg NIFTIs")
        if len(seg_nifti_list) == 0:
            print(f"# No NIFTI found -> skipping batch-element")
            continue

        print("# -> start merging")
        assert len(seg_nifti_list) == 1
        seg_nifti = seg_nifti_list[0]
        Path(dirname(target_seg_path)).mkdir(parents=True, exist_ok=True)

        meta_info_json_path = glob.glob(join(dirname(seg_nifti), "*.json"), recursive=False)
        assert len(meta_info_json_path) == 1

        if len(meta_info_json_path) == 1 and exists(meta_info_json_path[0]):
            meta_info_json_path = meta_info_json_path[0]
            print("# Found DCMQI meta-json")
            with open(meta_info_json_path, 'r') as f:
                meta_info = json.load(f)

            if "segmentAttributes" in meta_info:
                for entries in meta_info["segmentAttributes"]:
                    seg_id = None
                    extracted_label_tag = None
                    for part in entries:
                        if "labelID" in part and (seg_id is None or str(part["labelID"]) == seg_id):
                            if "labelID" in part and seg_id is None:
                                seg_id = int(part["labelID"])
                            if "SegmentLabel" in part:
                                extracted_label_tag = part["SegmentLabel"]
                            elif "TrackingIdentifier" in part:
                                extracted_label_tag = part["TrackingIdentifier"]
                    assert seg_id is not None and extracted_label_tag is not None
                    label_names_found[extracted_label_tag] = seg_id

        if copy_target_data:
            shutil.copy2(seg_nifti, target_seg_path)
        else:
            shutil.move(seg_nifti, target_seg_path)

        print("# Adding dataset ...")
        template_dataset_json[dataset_id].append(
            {
                "image": join("./", "imagesTr", base_file_path),
                "label": join("./", "labelsTr", base_file_path)
            }
        )
        print("# -> element DONE!")

    print("#")
    print(f"# {dataset_id} dataset DONE !")
    print("#")


task_name = os.getenv("TASK", "")
licence = os.getenv("LICENCE", "N/A")
version = os.getenv("VERSION", "N/A")
training_name = task_name
training_description = os.getenv("TRAINING_DESCRIPTION", "nnUNet training")
training_reference = os.getenv("TRAINING_REFERENCE", "nnUNet")
shuffle_seed = int(os.getenv("SHUFFLE_SEED", "0")),
network_trainer = os.getenv("TRAIN_NETWORK_TRAINER", "N/A")
model_architecture = os.getenv("MODEL", "UNKNOWN")  # -> model 2d,3d_lowres etc
test_percentage = int(os.getenv("TEST_PERCENTAGE", "0"))
copy_target_data = True if os.getenv("PREP_COPY_DATA", "False").lower() == "true" else False
tensor_size = os.getenv("TENSOR_SIZE", "3D")
instance_name = os.getenv("INSTANCE_NAME", "N/A").replace(" ", "_")
max_epochs = os.getenv("TRAIN_MAX_EPOCHS", "N/A")

input_modalities = os.getenv("PREP_MODALITIES", "")
input_label_dirs = os.getenv("PREP_LABEL_DIRS", "")
exit_on_issue = True if os.getenv("PREP_EXIT_ON_ISSUE", "True").lower() == "true" else False
input_modality_dirs = os.getenv("INPUT_MODALITY_DIRS", "")

batch_dir = join('/', os.environ["WORKFLOW_DIR"], os.environ["BATCH_NAME"])
operator_out_dir = join('/', os.environ["WORKFLOW_DIR"], os.environ["OPERATOR_OUT_DIR"])
task_dir = join(operator_out_dir, "nnUNet_raw_data", os.environ["TASK"])

use_nifti_labels = True if os.getenv("PREP_USE_NIFITI_LABELS", "False").lower() == "true" else False
global_label_index = 0

thread_count = 5

if input_label_dirs == "" or input_modalities == "" or input_modality_dirs == "":
    print("#")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("# ")
    print("# Needed Env not set!")
    print(f"# LABEL_DIRS:      {input_label_dirs}")
    print(f"# MODALITY_DIRS:   {input_modality_dirs}")
    print(f"# PREP_MODALITIES: {input_modalities}")
    print("# ")
    print("# ")
    print("# -> ABORT!")
    print("# ")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("# ")
    exit(1)

Path(task_dir).mkdir(parents=True, exist_ok=True)

print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
print("# ")
print("# Starting DatasetCreateOperator:")
print("# ")
print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

series_list_tmp = [f.path for f in os.scandir(batch_dir) if f.is_dir()]
series_list_tmp.sort()

series_list=[]
for series in series_list_tmp:
    print("######################################################################")
    print(f"# Check series {series} for seg-check files...")
    seg_check_files = glob.glob(join(series, "seg-check", "*.nii.gz"), recursive=False)
    if len(seg_check_files) != 1:
        print("# ")
        print("# Seg-check issue -> skipping!")
        print(f"# seg_check_files: {seg_check_files}")
        print("# ")
    else:
        print(f"# OK!")
        series_list.append(series)
    print(f"# ")

modality = {}
input_modalities = input_modalities.split(",")
input_label_dirs = input_label_dirs.split(",")
input_modality_dirs = input_modality_dirs.split(",")
for i in range(0, len(input_modalities)):
    modality[f"{i}"] = input_modalities[i]

label_extraction_dirs = {}
for input_series in series_list:
    label_extraction_dirs[input_series] = []
    for input_label_dir in input_label_dirs:
        label_extraction_dirs[input_series].append(input_label_dir)

template_dataset_json = {
    "name": training_name,
    "shuffle_seed": shuffle_seed,
    "network_trainer": network_trainer,
    "model": [model_architecture],
    "description": training_description,
    "reference": training_reference,
    "licence": licence,
    "release": version,
    "tensorImageSize": tensor_size,
    "modality": modality,
    "labels": None,
    "numTraining": 0,
    "numTest": 0,
    "instance_name": instance_name,
    "max_epochs": max_epochs,
    "training": [],
    "test": []


}

series_count = len(series_list)
test_count = round((series_count/100)*test_percentage)
train_count = series_count - test_count

template_dataset_json["numTraining"] = train_count
template_dataset_json["numTest"] = test_count

print("# ")
print(f"# All series count:  {series_count}")
print(f"# Train-datset-size: {train_count}")
print(f"# Test-datset-size:  {test_count}")
print("# ")
print(f"# copy_target_data:    {copy_target_data}")
print(f"# use_nifti_labels:    {use_nifti_labels}")
print("# ")

if len(modality) != len(input_modality_dirs):
    print("# ")
    print("# len(modality) != len(input_operators)")
    print("# You have to specify {} input_operators!".format(len(modality)))
    print("# Expected modalities:")
    print(json.dumps(modality, indent=4, sort_keys=False))
    print("# ")
    print("# ")
    exit(1)

if (train_count + test_count) != series_count:
    print("# Something went wrong! -> dataset-splits != series-count!")
    exit(1)

print("# Using shuffle-seed: {}".format(shuffle_seed))
random.seed(shuffle_seed)
random.shuffle(series_list)
print("# ")

train_series = series_list[:train_count]
test_series = series_list[train_count:]

label_names_found = {}

prepare_dataset(datset_list=train_series, dataset_id="training")
prepare_dataset(datset_list=test_series, dataset_id="test")

print("#")
print("# Creating dataset.json ....")
print("#")
labels = {
    "0": "Clear Label",
}
for key, value in label_names_found.items():
    labels[str(value)] = key

print("# Extracted labels:")
sorted_labels = {}
for key in sorted(labels.keys(), key=int):
    sorted_labels[str(key)] = labels[key]
print(json.dumps(sorted_labels, indent=4, sort_keys=False))
template_dataset_json["labels"] = sorted_labels
print("#")
print("#")

with open(join(task_dir, 'dataset.json'), 'w') as fp:
    json.dump(template_dataset_json, fp, indent=4, sort_keys=False)

with open(join('/', os.environ["WORKFLOW_DIR"], os.environ["OPERATOR_OUT_DIR"], 'dataset.json'), 'w') as fp:
    # One could make this smoother, so not saving a copy of the file...
    json.dump(template_dataset_json, fp, indent=4, sort_keys=False)
    

print("#############################################################")
print("#")
print("# Dataset preparation done!")
print("#")
print("#############################################################")
