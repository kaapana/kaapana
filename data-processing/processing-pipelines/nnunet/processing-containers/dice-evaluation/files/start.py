import os
import json
from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
from multiprocessing.pool import ThreadPool
from pathlib import Path
import numpy as np
import nibabel as nib
import torch
import pandas as pd
from monai.metrics import compute_meandice, compute_average_surface_distance
from pprint import pprint
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib import rcParams

rcParams.update({"figure.autolayout": True})

# Counter to check if smth has been processed
processed_count = 0
model_counter = 0

# os.environ['WORKFLOW_DIR'] = str("/home/jonas/Downloads/dag-data/nnunet-ensemble-210512095519706991")
# os.environ['BATCH_NAME'] = str("nnunet-dataset")
# os.environ['OPERATOR_IN_DIR'] = str("seg-check-inference")
# os.environ['OPERATOR_OUT_DIR'] = str("dice-evaluation")
# os.environ['GT_IN_DIR'] = str("seg-check-gt")
# os.environ['ENSEMBLE_IN_DIR'] = str("seg-check-ensemble")
# os.environ['ANONYMIZE'] = str("True")
# os.environ['THREADS'] = str("1")

workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None

batch_name = getenv("BATCH_NAME", "None")
batch_name = batch_name if batch_name.lower() != "none" else None
assert batch_name is not None

operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
assert operator_in_dir is not None

gt_in_dir = getenv("GT_IN_DIR", "None")
gt_in_dir = gt_in_dir if gt_in_dir.lower() != "none" else None
assert gt_in_dir is not None

ensemble_in_dir = getenv("ENSEMBLE_IN_DIR", "None")
ensemble_in_dir = ensemble_in_dir if ensemble_in_dir.lower() != "none" else None
assert ensemble_in_dir is not None

operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
assert operator_out_dir is not None

anonymize = getenv("ANONYMIZE", "False")
anonymize = True if anonymize.lower() == "true" else False

include_background = getenv("INCLUDE_BAKGROUND", "False")
include_background = True if include_background.lower() == "true" else False

parallel_processes = getenv("THREADS", "1")
parallel_processes = (
    int(parallel_processes) if parallel_processes.lower() != "none" else None
)
assert parallel_processes is not None

# File-extension to search for in the input-dir
input_file_extension = "*.nii.gz"

# How many processes should be started?
dice_results = {}


def get_seg_info(input_nifti):
    print(f"# Get seg configuration for: {basename(input_nifti)}")
    model_id = (
        f"-{basename(input_nifti).replace('.nii.gz','').split('-')[-1]}"
        if "-" in basename(input_nifti)
        else ""
    )
    seg_nifti_id = basename(input_nifti).replace(".nii.gz", "")
    json_files_found = glob(join(dirname(input_nifti), "*.json"), recursive=False)
    json_files_found = [
        meta_json_path
        for meta_json_path in json_files_found
        if "model_combinations" not in meta_json_path
    ]

    print(f"# input_nifti: {input_nifti}")
    print(f"# model_id: {model_id}")
    meta_json_path = input_nifti.replace(".nii.gz", ".json")
    print(f"# meta-info-file: {meta_json_path}")
    assert exists(meta_json_path)
    gen_seg_info = {}
    with open(meta_json_path, "rb") as f:
        meta_info = json.load(f)

    if "segmentAttributes" in meta_info:
        for entries in meta_info["segmentAttributes"]:
            for part in entries:
                if "labelID" in part:
                    label_int = int(part["labelID"])
                    if "SegmentLabel" in part:
                        label_name = part["SegmentLabel"]

                    elif "TrackingIdentifier" in part:
                        label_name = part["TrackingIdentifier"]
                gen_seg_info[label_name] = label_int

    if "seg-check-inference" in input_nifti:
        model_id_info_file = join(
            dirname(input_nifti).replace("seg-check-inference", "do-inference"),
            f"seg_info{model_id}.json",
        )
        print(f"# model_id_info_file: {model_id_info_file}")
        assert exists(model_id_info_file)

        with open(model_id_info_file, "rb") as f:
            model_info = json.load(f)

        assert "task_id" in model_info
        model_id = model_info["task_id"]
    elif "seg-check-ensemble" in input_nifti:
        # model_id_info_file = join(dirname(input_nifti).replace("seg-check-ensemble", "do-ensemble"), f"seg_info{model_id}.json")
        model_id = "ensemble"
    else:
        print(f"# Could not find model info for: {input_nifti}")

    print(f"# extracted model-id: {model_id}")
    return model_id, gen_seg_info


def check_prediction_info(seg_info):
    global global_seg_check_info

    for label_key, encoding_int in seg_info.items():
        if label_key not in global_seg_check_info:
            pass
        elif global_seg_check_info[label_key] != encoding_int:
            print("# ")
            print("# seg_info:")
            print(json.dumps(seg_info, indent=4, sort_keys=True, default=str))
            print("# ")
            print("# ")
            print("# global_seg_check_info:")
            print(
                json.dumps(global_seg_check_info, indent=4, sort_keys=True, default=str)
            )
            print("# ")
            print("# Issue with prediction config!")
            return False

    return True


def get_metric_score(input_data):
    global dice_results, global_seg_check_info, max_label_encoding, processed_count, include_background, model_counter
    batch_id, single_model_pred_files, gt_file, ensemble_pred_file = input_data

    results = {}

    ground_trouth = nib.load(gt_file).get_fdata().astype(int)
    one_hot_encoding_gt = (
        (np.arange(max_label_encoding + 1) == ground_trouth[..., None])
        .astype(int)
        .transpose()
    )
    one_hot_encoding_gt = np.expand_dims(one_hot_encoding_gt, axis=0)
    ground_trouth = None
    gt_tensor = torch.from_numpy(one_hot_encoding_gt)
    one_hot_encoding_gt = None

    for model_pred_file in single_model_pred_files:
        info_json = model_pred_file.replace("nii.gz", "json")
        pred_file_id = basename(model_pred_file).replace(".nii.gz", "")

        model_id, seg_info = get_seg_info(input_nifti=model_pred_file)
        if seg_info is None:
            print(f"# info_json does not exist: {info_json}")
        assert seg_info is not None
        assert check_prediction_info(seg_info)

        assert model_id not in results
        results[model_id] = {}

        single_model_prediction = nib.load(model_pred_file).get_fdata().astype(int)
        one_hot_encoding_pred = (
            (np.arange(max_label_encoding + 1) == single_model_prediction[..., None])
            .astype(int)
            .transpose()
        )
        one_hot_encoding_pred = np.expand_dims(one_hot_encoding_pred, axis=0)
        single_model_prediction = None
        pred_tensor = torch.from_numpy(one_hot_encoding_pred)
        one_hot_encoding_pred = None
        dice_scores = compute_meandice(
            y_pred=pred_tensor, y=gt_tensor, include_background=include_background
        ).numpy()[0]
        asd_scores = compute_average_surface_distance(
            y_pred=pred_tensor, y=gt_tensor, include_background=include_background
        ).numpy()[0]
        pred_tensor = None
        print(f"# {model_pred_file} -> dice_scores: {list(dice_scores)}")
        print(f"# {model_pred_file} -> asd_scores: {list(asd_scores)}")
        results[model_id] = {
            pred_file_id: {
                "dice_scores": list(dice_scores),
                "asd_scores": list(np.float32(asd_scores)),
            }
        }  # numpy casting to have same format as dice_score
    if ensemble_pred_file is not None:
        info_json = ensemble_pred_file.replace(".nii.gz", ".json")
        print(f"# info_json: {info_json}")
        print(f"# ensemble_pred_file: {ensemble_pred_file}")
        model_id, seg_info = get_seg_info(input_nifti=ensemble_pred_file)
        if seg_info is None:
            print(f"# info_json does not exist: {info_json}")
        assert seg_info is not None
        assert check_prediction_info(seg_info)

        assert "ensemble" not in results

        ensemble_file_id = basename(ensemble_pred_file).replace(".nii.gz", "")
        ensemble_prediction = nib.load(ensemble_pred_file).get_fdata().astype(int)
        one_hot_encoding_ensemble = (
            (np.arange(max_label_encoding + 1) == ensemble_prediction[..., None])
            .astype(int)
            .transpose()
        )
        one_hot_encoding_ensemble = np.expand_dims(one_hot_encoding_ensemble, axis=0)
        ensemble_prediction = None
        ensemble_tensor = torch.from_numpy(one_hot_encoding_ensemble)
        one_hot_encoding_ensemble = None

        dice_scores = compute_meandice(
            y_pred=ensemble_tensor, y=gt_tensor, include_background=include_background
        ).numpy()[0]
        asd_scores = compute_average_surface_distance(
            y_pred=ensemble_tensor, y=gt_tensor, include_background=include_background
        ).numpy()[0]

        pred_tensor = None

        print(f"# ensemble: {ensemble_pred_file} -> dice_scores: {list(dice_scores)}")
        print(f"# ensemble: {ensemble_pred_file} -> asd_scores: {list(asd_scores)}")
        results["ensemble"] = {
            ensemble_file_id: {
                "dice_scores": list(dice_scores),
                "asd_scores": list(np.float32(asd_scores)),
            }
        }

    return True, batch_id, results


print("##################################################")
print("#")
print("# Starting operator dice-evaluation:")
print("#")
print(f"# workflow_dir:     {workflow_dir}")
print(f"# batch_name:       {batch_name}")
print("#")
print(f"# operator_in_dir:  {operator_in_dir}")
print(f"# gt_in_dir:        {gt_in_dir}")
print(f"# ensemble_in_dir:  {ensemble_in_dir}")
print("#")
print(f"# operator_out_dir: {operator_out_dir}")
print(f"# anonymize:         {anonymize}")
print("#")
print(f"# include_background: {include_background}")
print("#")
print("##################################################")
print("#")
print("# Starting processing on BATCH-ELEMENT-level ...")
print("#")
print("##################################################")
print("#")

seg_check_info_json_files = glob(join("/", workflow_dir, "global-seg-info", "*.json"))
assert len(seg_check_info_json_files) == 1

with open(seg_check_info_json_files[0]) as f:
    tmp_info_dict = json.load(f)

global_seg_check_info = {}
max_label_encoding = 0
for label_key, int_encoding in tmp_info_dict.items():
    int_encoding = int(int_encoding)
    max_label_encoding = (
        int_encoding if int_encoding > max_label_encoding else max_label_encoding
    )
    global_seg_check_info[label_key] = int_encoding

if "Clear Label" not in global_seg_check_info:
    global_seg_check_info["Clear Label"] = 0

queue_list = []
batch_output_dir = join("/", workflow_dir, operator_out_dir)
Path(batch_output_dir).mkdir(parents=True, exist_ok=True)

output_file = join(batch_output_dir, "dice_results.json")
# Loop for every batch-element (usually series)
batch_folders = sorted([f for f in glob(join("/", workflow_dir, batch_name, "*"))])
for batch_element_dir in batch_folders:
    print("#")
    print(f"# Processing batch-element {batch_element_dir}")
    print("#")
    batch_id = basename(batch_element_dir)
    single_model_input_dir = join(batch_element_dir, operator_in_dir)
    ensemble_input_dir = join(batch_element_dir, ensemble_in_dir)
    gt_input_dir = join(batch_element_dir, gt_in_dir)

    single_model_pred_files = glob(join(single_model_input_dir, input_file_extension))
    gt_files = glob(join(gt_input_dir, input_file_extension))
    ensemble_pred_files = glob(join(ensemble_input_dir, input_file_extension))

    print(f"#")
    print(f"# found:")
    print(f"#")
    print(
        f"# {len(single_model_pred_files)} single_model_pred_files at {single_model_input_dir}"
    )
    print(f"# {len(gt_files)} gt_files at {gt_input_dir}")
    print(f"# {len(ensemble_pred_files)} ensemble_pred_files at {ensemble_input_dir}")
    print(f"#")
    assert len(gt_files) == 1
    gt_file = gt_files[0]
    assert len(single_model_pred_files) > 0

    assert len(ensemble_pred_files) < 2
    ensemble_pred_file = None
    if len(ensemble_pred_files) > 0:
        ensemble_pred_file = ensemble_pred_files[0]
        print(f"# Using ensemble-file: {ensemble_pred_file}")

    input_data = (batch_id, single_model_pred_files, gt_file, ensemble_pred_file)
    queue_list.append(input_data)
    print(f"# Adding data to the job-list ..")
    print(f"#")

print(f"#")
print(f"#")
print(
    f"# Starting {parallel_processes} parallel jobs -> job_count: {len(queue_list)} ..."
)
print(f"#")
print(f"#")
with ThreadPool(parallel_processes) as threadpool:
    results = threadpool.imap_unordered(get_metric_score, queue_list)
    for success, batch_id, result in results:
        if success:
            processed_count += 1
            print("#")
            print(f"# {batch_id}: ✓ {processed_count} / {len(queue_list)} successful")
            print("#")
            assert batch_id not in dice_results

            dice_results[batch_id] = result
        else:
            print("#")
            print(f"# {batch_id}: issue!")
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

print("#")
print(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
print("#")

print("# Writing results to json:")
print("# ")
print(json.dumps(dice_results, indent=4, sort_keys=True, default=str))
print("# ")
with open(output_file, "w", encoding="utf-8") as jsonData:
    json.dump(dice_results, jsonData, indent=4, sort_keys=True, default=str)

# with open(output_file) as f:
#     dice_results = json.load(f)
print("# Generating dataframes ... ")
result_table = []
for batch_id, model_results in dice_results.items():
    print(f"batch: {batch_id}")
    for model_id, file_results in model_results.items():
        print(f"model_id: {model_id}")
        for file_id, dice_info in file_results.items():
            print(f"file_id: {model_id}")
            for array_index in range(0, len(dice_info["dice_scores"])):
                class_label = list(global_seg_check_info.keys())[
                    list(global_seg_check_info.values()).index(array_index + 1)
                ]
                class_dice = float(dice_info["dice_scores"][array_index])
                class_asd = float(dice_info["asd_scores"][array_index])
                result_table.append(
                    [file_id, model_id, class_label, class_dice, class_asd]
                )

df_data = pd.DataFrame(
    result_table, columns=["Series", "Model", "Label", "Dice", "ASD"]
)
df_data.to_csv(join(batch_output_dir, "dice_results.csv"), sep="\t")

print("# DONE #")
