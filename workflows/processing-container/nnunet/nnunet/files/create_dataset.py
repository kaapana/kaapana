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

# To extract
modality = os.getenv("MODALITY", "")
labels = os.getenv("LABELS", "")

use_nifti_labels= True if os.getenv("PREP_USE_NIFITI_LABELS", "False").lower() == "true" else False

def extract_labels(nifti_seg_dirs):
    print(f"# Extract labels from: {nifti_seg_dirs}")
    count = 0
    labels = {
        "0": "Clear Label",
    }
    for nifti_seg_dir in nifti_seg_dirs:
        seg_niftis = glob.glob(os.path.join(nifti_seg_dir, "*.nii.gz"), recursive=True)
        for seg_nifti in seg_niftis:

            if use_nifti_labels:
                print("# Using NIFTI labels...")
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
                print(f"# Generating label-count: {count}")

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


label_in_dir = os.getenv('PREP_LABEL_DIR', "")
input_modalities = os.getenv("PREP_MODALITIES", "")
input_nifti_dirs = os.getenv("INPUT_NIFTI_DIRS", "")

if label_in_dir == "" or input_modalities == "" or input_nifti_dirs == "":
    print("")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("")
    print("Needed Env not set!")
    print(f"PREP_LABEL_DIR: {label_in_dir}")
    print(f"PREP_MODALITIES: {input_modalities}")
    print(f"INPUT_NIFTI_DIRS: {input_nifti_dirs}")
    print("")
    print("-> ABORT!")
    print("")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("")
    exit(1)

batch_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'])
operator_out_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_OUT_DIR'])
task_dir = os.path.join(operator_out_dir, "nnUNet_raw_data", os.environ['TASK'])
Path(task_dir).mkdir(parents=True, exist_ok=True)

print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
print("")
print("  Starting DatasetCreateOperator:")
print("")

series_list = [f.path for f in os.scandir(batch_dir) if f.is_dir()]
series_list.sort()

modality = {}
input_modalities = input_modalities.split(",")
input_nifti_dirs = input_nifti_dirs.split(",")
for i in range(0, len(input_modalities)):
    modality[f"{i}"] = input_modalities[i]

labels_extraction_dirs = [os.path.join(series_list[0], label_in_dir)]
labels = extract_labels(nifti_seg_dirs=labels_extraction_dirs)

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

print("")
print("All series count:  {}".format(series_count))
print("Train-datset-size: {}".format(train_count))
print("Test-datset-size:  {}".format(test_count))
print("")

if len(modality) != len(input_nifti_dirs):
    print("")
    print("len(modality) != len(input_operators)")
    print("You have to specify {} input_operators!".format(len(modality)))
    print("Expected modalities:")
    print(json.dumps(modality, indent=4, sort_keys=True))
    print("")
    print("")
    exit(1)

if (train_count + test_count) != series_count:
    print("Something went wrong! -> dataset-splits != series-count!")
    exit(1)

print("Using shuffle-seed: {}".format(shuffle_seed))
random.seed(shuffle_seed)
random.shuffle(series_list)
print("")

train_series = series_list[:train_count]
test_series = series_list[train_count:]

print("Preparing all train series: {}".format(len(train_series)))
for series in train_series:
    base_file_path = os.path.join("imagesTr", f"{os.path.basename(series)}.nii.gz")
    base_seg_path = os.path.join("labelsTr", f"{os.path.basename(series)}.nii.gz")

    for i in range(0, len(input_nifti_dirs)):
        modality_nifti_dir = os.path.join(series, input_nifti_dirs[i])

        modality_nifti = glob.glob(os.path.join(modality_nifti_dir, "*.nii.gz"), recursive=True)
        if len(modality_nifti) != 1:
            print("")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("")
            print("Error with training image-file!")
            print("Found {} files at: {}".format(len(modality_nifti), modality_nifti_dir))
            print("Expected only one file! -> abort.")
            print("")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("")
            exit(1)

        target_modality_path = os.path.join(task_dir, base_file_path.replace(".nii.gz", f"_{i:04}.nii.gz"))
        move_file(source=modality_nifti[0], target=target_modality_path)

    seg_nifti = glob.glob(os.path.join(series, label_in_dir, "*.nii.gz"), recursive=True)
    if len(seg_nifti) != 1:
        print("")
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("")
        print("Error with training seg-file!")
        print("Found {} files at: {}".format(len(seg_nifti), os.path.join(series, label_in_dir)))
        print("Expected only one file! -> abort.")
        print("")
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("")
        exit(1)

    target_seg_path = os.path.join(task_dir, base_seg_path)
    move_file(source=seg_nifti[0], target=target_seg_path)

    template_dataset_json["training"].append(
        {
            "image": os.path.join("./", base_file_path),
            "label": os.path.join("./", base_seg_path)
        }
    )

for series in test_series:
    print("Preparing test series: {}".format(series))
    base_file_path = os.path.join("imagesTs", f"{os.path.basename(series)}.nii.gz")
    base_seg_path = os.path.join("labelsTr", f"{os.path.basename(series)}.nii.gz")

    for i in range(0, len(input_nifti_dirs)):
        modality_nifti_dir = os.path.join(series, input_nifti_dirs)

        modality_nifti = glob.glob(os.path.join(modality_nifti_dir, "*.nii.gz"), recursive=True)
        if len(modality_nifti) != 1:
            print("")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("")
            print("Error with test image-file!")
            print("Found {} files at: {}".format(len(modality_nifti), modality_nifti_dir))
            print("Expected only one file! -> abort.")
            print("")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("")
            exit(1)

        target_modality_path = os.path.join(task_dir, base_file_path.replace(".nii.gz", f"_{i:04}.nii.gz"))
        move_file(source=modality_nifti[0], target=target_modality_path)

    # seg_dir = os.path.join(series, seg_input_operator.operator_out_dir)
    # seg_nifti = glob.glob(os.path.join(seg_dir, "*.nii.gz"), recursive=True)
    # if len(seg_nifti) != 1:
    #     print("")
    #     print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    #     print("")
    #     print("Error with test seg-file!")
    #     print("Found {} files at: {}".format(len(seg_nifti), seg_dir))
    #     print("Expected only one file! -> abort.")
    #     print("")
    #     print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    #     print("")
    #     exit(1)
    # target_seg_path = os.path.join(task_dir, base_seg_path)
    # move_file(source=seg_nifti[0], target=target_seg_path)

    template_dataset_json["test"].append(os.path.join("./", base_file_path))

with open(os.path.join(task_dir, 'dataset.json'), 'w') as fp:
    json.dump(template_dataset_json, fp, indent=4, sort_keys=True)

print("#############################################################")
print("")
print("  Dataset preparation done!")
print("")
print("#############################################################")
