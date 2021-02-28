import sys
import os
import glob
import json
import shutil
from pathlib import Path
import random
import pydicom
import nibabel as nib
import numpy as np
from collections import OrderedDict


def prepare_dataset(datset_list, dataset_id):
    global template_dataset_json, label_names_found, label_int
    print(f"# Preparing all {dataset_id} series: {train_series}")
    for series in datset_list:
        print("######################################################################")
        print("#")
        print("# Processing series:")
        print(f"# {series}")
        print("#")
        print("######################################################################")
        imagesTr_path = os.path.join(task_dir, "imagesTr")
        base_file_path = f"{os.path.basename(series)}.nii.gz"

        for i in range(0, len(input_modality_dirs)):
            modality_nifti_dir = os.path.join(series, input_modality_dirs[i])

            modality_nifti = glob.glob(os.path.join(
                modality_nifti_dir, "*.nii.gz"), recursive=True)
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
            target_modality_path = os.path.join(
                imagesTr_path, base_file_path.replace(".nii.gz", f"_{i:04}.nii.gz"))
            Path(os.path.dirname(target_modality_path)).mkdir(
                parents=True, exist_ok=True)
            if copy_target_data:
                shutil.copy2(modality_nifti, target_modality_path)
            else:
                shutil.move(modality_nifti, target_modality_path)

        target_seg_path = os.path.join(task_dir, "labelsTr", base_file_path)
        seg_nifti_list = []
        for label_dir in input_label_dirs:
            seg_niftis = glob.glob(os.path.join(series, label_dir, "*.nii.gz"), recursive=True)
            seg_nifti_list.extend(seg_niftis)

        print(f"# Found {len(seg_nifti_list)} seg NIFTIs -> start merging")

        example_img = nib.load(seg_nifti_list[0])
        combined = np.zeros_like(example_img.get_fdata().astype(int))

        for seg_nifti in seg_nifti_list:
            print(f"# Processing NIFTI: {seg_nifti}")
            if "--" in seg_nifti:
                label_tag = seg_nifti.split("--")[-1].split(".")[0].replace("_", " ")
            else:
                label_tag = str(label_int)

            nii_array = nib.load(seg_nifti).get_fdata().astype(int)
            nifti_labels = list(np.unique(nii_array))
            if 0 in nifti_labels:
                nifti_labels.remove(0)
            else:
                print("#")
                print(f"# Couldn't find a 'Clear Label' 0 in NIFTI: {seg_nifti}")
                print("#")
                exit(1)

            if len(nifti_labels) != 1:
                print("#")
                print(f"# More than one label found in NIFTI: {seg_nifti}")
                print(f"# Single label segmentation NIFTIs expected -> error")
                print("# ")
                exit(1)

            nifti_bin_encoding = nifti_labels[0]
            if label_tag not in label_names_found:
                print(f"# Adding label: {label_tag} ...")
                if use_nifti_labels:
                    label_int = nifti_bin_encoding
                    print(f"# -> using NIFTI encoding: {label_int}")
                else:
                    label_int += 1
                    print(f"# -> using default encoding: {label_int}")
                label_names_found[label_tag] = label_int
            else:
                print("# Label already present -> checking NIFTI encoding...")
                if label_names_found[label_tag] != nifti_bin_encoding:
                    print("#")
                    print("###################### WARNING ###################### ")
                    print("#")
                    print(f"# Label '{label_tag}' has already been found and the integer encoding differs to the NIFTI !")
                    print(f"# New NIFTI encoding:  {nifti_bin_encoding}")
                    print(f"# Existing encoding:   {label_names_found[label_tag] }")
                    print("#")
                    print(f"# -> replacing with original integer encoding: {nifti_bin_encoding} -> {label_names_found[label_tag]}")
                    print("#")
                    print("##################################################### ")
                    print("#")
                    nii_array = np.where(nii_array == nifti_bin_encoding, label_names_found[label_tag], nii_array)
                else:
                    print("# NIFTI encoding -> ok")

            print("# Merging NIFTI to Ground Truth ...")
            combined = np.maximum(combined, nii_array)
            print("# Merging OK")

        print(f"# Writing Ground Truth into {target_seg_path} ...")
        combined = nib.Nifti1Image(combined, example_img.affine, example_img.header)
        Path(os.path.dirname(target_seg_path)).mkdir(parents=True, exist_ok=True)
        combined.to_filename(target_seg_path)
        print("# GT file OK")

        if not copy_target_data:
            print("# Deleting input NIFTIs ...")
            for file_path in seg_nifti_list:
                os.remove(file_path)
        else:
            print("# Keeping input NIFTIs!")

        print("# Adding dataset ...")
        template_dataset_json[dataset_id].append(
            {
                "image": os.path.join("./", "imagesTr", base_file_path),
                "label": os.path.join("./", "labelsTr", base_file_path)
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
model_architecture = os.getenv("TRAIN_NETWORK", "UNKNOWN")  # -> model 2d,3d_lowres etc
test_percentage = int(os.getenv("TEST_PERCENTAGE", "0"))
copy_target_data = True if os.getenv("PREP_COPY_DATA", "False").lower() == "true" else False
tensor_size = os.getenv("TENSOR_SIZE", "3D")

input_modalities = os.getenv("PREP_MODALITIES", "")
input_label_dirs = os.getenv("PREP_LABEL_DIRS", "")
exit_on_issue = True if os.getenv("PREP_EXIT_ON_ISSUE", "True").lower() == "true" else False
input_modality_dirs = os.getenv("INPUT_MODALITY_DIRS", "")

batch_dir = os.path.join('/', os.environ["WORKFLOW_DIR"], os.environ["BATCH_NAME"])
operator_out_dir = os.path.join('/', os.environ["WORKFLOW_DIR"], os.environ["OPERATOR_OUT_DIR"])
task_dir = os.path.join(operator_out_dir, "nnUNet_raw_data", os.environ["TASK"])

use_nifti_labels = True if os.getenv("PREP_USE_NIFITI_LABELS", "False").lower() == "true" else False

if input_label_dirs == "" or input_modalities == "" or input_modality_dirs == "":
    print("#")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("# ")
    print("# Needed Env not set!")
    print(f"# LABEL_DIRS:      {input_label_dirs}")
    print(f"# MODALITY_DIRS:   {input_modality_dirs}")
    print(f"# PREP_MODALITIES: {input_modalities}")
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

series_list = [f.path for f in os.scandir(batch_dir) if f.is_dir()]
series_list.sort()

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

label_int = 0
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
print(json.dumps(labels, indent=4, sort_keys=False))
template_dataset_json["labels"] = labels
print("#")
print("#")

with open(os.path.join(task_dir, 'dataset.json'), 'w') as fp:
    json.dump(template_dataset_json, fp, indent=4, sort_keys=False)

print("#############################################################")
print("#")
print("# Dataset preparation done!")
print("#")
print("#############################################################")
