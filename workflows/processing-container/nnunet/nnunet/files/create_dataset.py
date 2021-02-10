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


def extract_labels(label_extraction_dirs):
    use_nifti_labels = True if os.getenv("PREP_USE_NIFITI_LABELS", "False").lower() == "true" else False
    verify_all_datasets = True if os.getenv("PREP_VERIFY_ALL_LABELS", "False").lower() == "true" else False
    print("#")
    print("# Starting extract_labels ...")
    print("#")
    print(f"# use_nifti_labels:    {use_nifti_labels}")
    print(f"# verify_all_datasets: {verify_all_datasets}")
    print("#")

    labels_dict = {}
    for input_series, label_dirs in label_extraction_dirs.items():
        count = 0
        labels = {
            "0": "Clear Label",
        }
        for label_dir in label_dirs:
            seg_niftis = glob.glob(os.path.join(input_series, label_dir, "*.nii.gz"), recursive=True)
            for seg_nifti in seg_niftis:

                if use_nifti_labels:
                    nifti_labels = [int(i) for i in np.unique(nib.load(seg_nifti).get_fdata())]
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

                    count = nifti_labels[0]
                else:
                    count += 1

                dict_key = f"{count}"
                if dict_key not in labels:
                    labels[dict_key] = seg_nifti.split("_")[-1].split(".")[0]

                else:
                    print("#")
                    print(f"# Label {dict_key} already found in labels.")
                    print(json.dumps(labels, indent=4, sort_keys=True))
                    print(f"# Label repetition -> error !")
                    print("#")
                    exit(1)

        labels_dict[os.path.join(input_series, label_dir)] = labels
        if not verify_all_datasets:
            break

    if verify_all_datasets:
        print("# Checking all extracted labels...")
        last_labels = None
        last_label_dir = None

        for label_dir, labels in labels_dict.items():
            if last_labels != None and last_labels != labels:
                print("#")
                print("# Error while checking all labels!")
                print(f"# last: {last_label_dir}")
                print(json.dumps(last_labels, indent=4, sort_keys=True))
                print("#")
                print(f"# last: {label_dir}")
                print(json.dumps(labels, indent=4, sort_keys=True))
                print("#")
                print("# ABORT")
                print("#")
                exit(1)

            last_labels = labels
            last_label_dir = label_dir

        print("# Done")

    print("# Extracted labels:")
    labels = OrderedDict(sorted(labels.items(), key=lambda t: t[0]))
    print(json.dumps(labels, indent=4, sort_keys=True))
    print("#")
    if len(labels) == 1:
        print(f"# No labels could be extracted!")
        exit(1)
    return labels


def move_file(source, target):
    Path(os.path.dirname(target)).mkdir(parents=True, exist_ok=True)
    if copy_target_data:
        shutil.copy2(source, target)
    else:
        shutil.move(source, target)


task_name = os.getenv("TASK", "")
licence = os.getenv("LICENCE", "NA")
version = os.getenv("VERSION", "NA")
training_name = task_name
training_description = os.getenv("TRAINING_DESCRIPTION", "nnUNet training")
training_reference = os.getenv("TRAINING_REFERENCE", "nnUNet")
shuffle_seed = int(os.getenv("SHUFFLE_SEED", "0")),
test_percentage = int(os.getenv("TEST_PERCENTAGE", "0"))
copy_target_data = True if os.getenv("COPY_DATA", "False").lower() == "true" else False
tensor_size = os.getenv("TENSOR_SIZE", "3D")

input_modalities = os.getenv("PREP_MODALITIES", "")
input_label_dirs = os.getenv("PREP_LABEL_DIRS", "")
input_modality_dirs = os.getenv("INPUT_MODALITY_DIRS", "")

batch_dir = os.path.join('/', os.environ["WORKFLOW_DIR"], os.environ["BATCH_NAME"])
operator_out_dir = os.path.join('/', os.environ["WORKFLOW_DIR"], os.environ["OPERATOR_OUT_DIR"])
task_dir = os.path.join(operator_out_dir, "nnUNet_raw_data", os.environ["TASK"])

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

labels, nifti_seg_path_list = extract_labels(label_extraction_dirs=label_extraction_dirs)
template_dataset_json = {
    "name": training_name,
    "description": training_description,
    "reference": training_reference,
    "licence": licence,
    "relase": version,
    "tensorImageSize": tensor_size,
    "modality": modality,
    "labels": labels,
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
print("# All series count:  {}".format(series_count))
print("# Train-datset-size: {}".format(train_count))
print("# Test-datset-size:  {}".format(test_count))
print("# ")

if len(modality) != len(input_modality_dirs):
    print("# ")
    print("# len(modality) != len(input_operators)")
    print("# You have to specify {} input_operators!".format(len(modality)))
    print("# Expected modalities:")
    print(json.dumps(modality, indent=4, sort_keys=True))
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

print("# Preparing all train series: {}".format(len(train_series)))
for series in train_series:
    base_file_path = os.path.join("imagesTr", f"{os.path.basename(series)}.nii.gz")

    for i in range(0, len(input_modality_dirs)):
        modality_nifti_dir = os.path.join(series, input_modality_dirs[i])

        modality_nifti = glob.glob(os.path.join(modality_nifti_dir, "*.nii.gz"), recursive=True)
        if len(modality_nifti) != 1:
            print("# ")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("# ")
            print("# Error with training image-file!")
            print("# Found {} files at: {}".format(len(modality_nifti), modality_nifti_dir))
            print("# Expected only one file! -> abort.")
            print("# ")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("# ")
            exit(1)

        target_modality_path = os.path.join(task_dir, base_file_path.replace(".nii.gz", f"_{i:04}.nii.gz"))
        move_file(source=modality_nifti[0], target=target_modality_path)

    
    target_seg_path = os.path.join(task_dir, "labelsTr", f"{os.path.basename(series)}.nii.gz")
    seg_nifti_list = []
    for label_dir in input_label_dirs:
        seg_niftis = glob.glob(os.path.join(series, label_dir, "*.nii.gz"), recursive=True)
        seg_nifti_list.extend(seg_niftis)

    example_img = nib.load(seg_nifti_list[0])
    combined = nib.funcs.concat_images(seg_nifti_list, check_affines=True, axis=None)
    combined = np.maximum.reduce(combined.get_fdata(), axis=3)
    combined = nib.Nifti1Image(combined, example_img.affine, example_img.header)
    combined.to_filename(target_seg_path)

    template_dataset_json["training"].append(
        {
            "image": os.path.join("./", base_file_path),
            "label": os.path.join("./", base_seg_path)
        }
    )

print("# Preparing all test series: {}".format(len(test_series)))
for series in test_series:
    base_file_path = os.path.join("imagesTr", f"{os.path.basename(series)}.nii.gz")

    for i in range(0, len(input_modality_dirs)):
        modality_nifti_dir = os.path.join(series, input_modality_dirs[i])

        modality_nifti = glob.glob(os.path.join(modality_nifti_dir, "*.nii.gz"), recursive=True)
        if len(modality_nifti) != 1:
            print("# ")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("# ")
            print("# Error with test image-file!")
            print("# Found {} files at: {}".format(len(modality_nifti), modality_nifti_dir))
            print("# Expected only one file! -> abort.")
            print("# ")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("# ")
            exit(1)

        target_modality_path = os.path.join(task_dir, base_file_path.replace(".nii.gz", f"_{i:04}.nii.gz"))
        move_file(source=modality_nifti[0], target=target_modality_path)

    
    target_seg_path = os.path.join(task_dir, "labelsTr", f"{os.path.basename(series)}.nii.gz")
    seg_nifti_list = []
    for label_dir in input_label_dirs:
        seg_niftis = glob.glob(os.path.join(series, label_dir, "*.nii.gz"), recursive=True)
        seg_nifti_list.extend(seg_niftis)

    example_img = nib.load(seg_nifti_list[0])
    combined = nib.funcs.concat_images(seg_nifti_list, check_affines=True, axis=None)
    combined = np.maximum.reduce(combined.get_fdata(), axis=3)
    combined = nib.Nifti1Image(combined, example_img.affine, example_img.header)
    combined.to_filename(target_seg_path)

    template_dataset_json["test"].append(
        {
            "image": os.path.join("./", base_file_path),
            "label": os.path.join("./", base_seg_path)
        }
    )

with open(os.path.join(task_dir, 'dataset.json'), 'w') as fp:
    json.dump(template_dataset_json, fp, indent=4, sort_keys=True)

print("#############################################################")
print("#")
print("# Dataset preparation done!")
print("#")
print("#############################################################")
