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
from monai.metrics import compute_meandice
from pprint import pprint
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams.update({'figure.autolayout': True})

# Counter to check if smth has been processed
processed_count = 0

os.environ['WORKFLOW_DIR'] = str("/home/jonas/Downloads/dice_test_data/nnunet-ensemble-210506020956539136")
os.environ['BATCH_NAME'] = str("nnunet-cohort")
os.environ['OPERATOR_IN_DIR'] = str("single-model-prediction")
os.environ['OPERATOR_OUT_DIR'] = str("dice-evaluation")
os.environ['GT_IN_DIR'] = str("seg-check-gt")
os.environ['ENSEMBLE_IN_DIR'] = str("ensemble-prediction")
os.environ['ANONYMIZE'] = str("True")
os.environ['THREADS'] = str("1")


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

parallel_processes = getenv("THREADS", "1")
parallel_processes = int(parallel_processes) if parallel_processes.lower() != "none" else None
assert parallel_processes is not None

# File-extension to search for in the input-dir
input_file_extension = "*.nii.gz"

# How many processes should be started?
dice_results = {}

def create_plots(data_table, table_name, result_dir):
    print(f"# Creating boxplots: {table_name}")
    os.makedirs(result_dir, exist_ok=True)

    plot_labels = sorted(list(data_table.Model.unique()))
    if "ensemble" in plot_labels:
        plot_labels.append(plot_labels.pop(plot_labels.index('ensemble')))

    fig, ax1 = plt.subplots(1, 1, figsize=(12, 14))
    box_plot = sns.boxplot(x="Model", y="Dice", hue="Label", palette="Set3", data=data_table, ax=ax1, order=plot_labels)
    box_plot.set_xticklabels(box_plot.get_xticklabels(), rotation=40, ha="right")

    box = box_plot.get_position()
    box_plot.set_position([box.x0, box.y0, box.width * 0.85, box.height])  # resize position
    box_plot.legend(loc='center right', bbox_to_anchor=(1.22, 0.5), ncol=1)
    plt.tight_layout()
    fig.savefig(join(result_dir, f"pdf_results_{table_name}.pdf"))
    fig.savefig(join(result_dir, f"png_results_{table_name}.png"), dpi=fig.dpi)
    # plt.show()
    print("# DONE")

def get_dice_score(input_data):
    global dice_results, global_seg_check_info, max_label_encoding, processed_count

    single_model_pred_files, gt_file, ensemble_pred_file = input_data

    ground_trouth = nib.load(gt_file).get_fdata().astype(int)
    one_hot_encoding_gt = (np.arange(max_label_encoding+1) == ground_trouth[..., None]).astype(int).transpose()
    one_hot_encoding_gt = np.expand_dims(one_hot_encoding_gt, axis=0)
    ground_trouth = None
    gt_tensor = torch.from_numpy(one_hot_encoding_gt)
    one_hot_encoding_gt = None

    gt_file_id = basename(gt_file).replace(".nii.gz", "")
    if gt_file_id not in dice_results:
        dice_results[gt_file_id] = {
            "models": {},
            "ensemble": {}
        }

    if ensemble_pred_file is not None:
        ensemble_file_id = basename(ensemble_pred_file).replace(".nii.gz", "")
        if ensemble_file_id in dice_results[gt_file_id]["ensemble"]:
            ensemble_pred_file = None

    for model_pred_file in single_model_pred_files:
        info_json = model_pred_file.replace("nii.gz", "json")
        pred_file_id = basename(model_pred_file).replace(".nii.gz", "")
        pred_file_id=f"{pred_file_id}_{processed_count}" #TODO
        assert pred_file_id not in dice_results[gt_file_id]["models"]

        seg_info = None
        if exists(info_json):
            with open(info_json) as f:
                seg_info = json.load(f)

        assert seg_info is not None

        single_model_prediction = nib.load(model_pred_file).get_fdata().astype(int)
        one_hot_encoding_pred = (np.arange(max_label_encoding+1) == single_model_prediction[..., None]).astype(int).transpose()
        one_hot_encoding_pred = np.expand_dims(one_hot_encoding_pred, axis=0)
        single_model_prediction = None
        pred_tensor = torch.from_numpy(one_hot_encoding_pred)
        one_hot_encoding_pred = None

        dice_scores = compute_meandice(y_pred=pred_tensor, y=gt_tensor, include_background=True).numpy()
        pred_tensor = None
        dice_results[gt_file_id]["models"][pred_file_id] = dice_scores

    if ensemble_pred_file is not None:
        info_json = ensemble_pred_file.replace("nii.gz", "json")
        seg_info = None
        if exists(info_json):
            with open(info_json) as f:
                seg_info = json.load(f)

        assert seg_info is not None

        ensemble_prediction = nib.load(ensemble_pred_file).get_fdata().astype(int)
        one_hot_encoding_ensemble = (np.arange(max_label_encoding+1) == ensemble_prediction[..., None]).astype(int).transpose()
        one_hot_encoding_ensemble = np.expand_dims(one_hot_encoding_ensemble, axis=0)
        ensemble_prediction = None
        ensemble_tensor = torch.from_numpy(one_hot_encoding_ensemble)
        one_hot_encoding_ensemble = None

        dice_scores = compute_meandice(y_pred=ensemble_tensor, y=gt_tensor, include_background=True).numpy()
        pred_tensor = None
        assert ensemble_file_id not in dice_results[gt_file_id]["ensemble"]
        dice_results[gt_file_id]["ensemble"][ensemble_file_id] = dice_scores

    return True, gt_file_id


print("##################################################")
print("#")
print("# Starting operator xyz:")
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
print("##################################################")
print("#")
print("# Starting processing on BATCH-ELEMENT-level ...")
print("#")
print("##################################################")
print("#")

# seg_check_info_json_files = glob(join('/', workflow_dir, gt_in_dir, "*.json"))
# assert len(seg_check_info_json_files) == 1

# with open(seg_check_info_json_files[0]) as f:
#     tmp_info_dict = json.load(f)

# global_seg_check_info={}
# max_label_encoding = 0
# for label_key, int_encoding in tmp_info_dict:
#     int_encoding=int(int_encoding)
#     max_label_encoding = int_encoding if int_encoding > max_label_encoding else max_label_encoding
#     global_seg_check_info[int_encoding]=label_key


# queue_list = []
# batch_output_dir = join('/', workflow_dir, operator_out_dir)
# Path(batch_output_dir).mkdir(parents=True, exist_ok=True)

# output_file = join(batch_output_dir,"dice_results.json")
# # Loop for every batch-element (usually series)
# batch_folders = [f for f in glob(join('/', workflow_dir, batch_name, '*'))]
# for batch_element_dir in batch_folders:
#     print("#")
#     print(f"# Processing batch-element {batch_element_dir}")
#     print("#")
#     single_model_input_dir = join(batch_element_dir, operator_in_dir)
#     ensemble_output_dir = join(batch_element_dir, ensemble_in_dir)
#     gt_input_dir = join(batch_element_dir, gt_in_dir)

#     single_model_pred_files = glob(join(single_model_input_dir, input_file_extension))
#     assert len(single_model_pred_files) > 0

#     ensemble_pred_files = glob(join(ensemble_output_dir, input_file_extension))
#     # assert len(ensemble_pred_files) == 1

#     gt_files = glob(join(gt_input_dir, input_file_extension))
#     assert len(gt_files) == 1

#     gt_file = gt_files[0]
#     ensemble_pred_file = ensemble_pred_files[0]

#     input_data = (single_model_pred_files, gt_file, ensemble_pred_file)
#     queue_list.append(input_data)
#     print(f"# Adding data to the job-list ..")
#     print(f"#")

# print(f"#")
# print(f"#")
# print(f"# Starting {parallel_processes} parallel jobs -> job_count: {len(queue_list)} ...")
# print(f"#")
# print(f"#")
# results = ThreadPool(parallel_processes).imap_unordered(get_dice_score, queue_list)
# for result, gt_file_id in results:
#     if result:
#         processed_count += 1
#         print("#")
#         print(f"# {gt_file_id}: ✓ {processed_count} / {len(queue_list)} successful")
#         print("#")
#     else:
#         print("#")
#         print(f"# {gt_file_id}: issue!")
#         print("#")

# if processed_count == 0:
#     print("#")
#     print("##################################################")
#     print("#")
#     print("##################  ERROR  #######################")
#     print("#")
#     print("# ----> NO FILES HAVE BEEN PROCESSED!")
#     print("#")
#     print("##################################################")
#     print("#")
#     exit(1)

# print("#")
# print(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
# print("#")

# print("# Writing results to json..")
# with open(output_file, "w", encoding='utf-8') as jsonData:
#     json.dump(dice_results, jsonData, indent=4, sort_keys=True,default=str)


json_path = "/home/jonas/Downloads/dice_test_data/nnunet-ensemble-210506020956539136/dice-evaluation/dice_results.json"
with open(json_path) as f:
    dice_results = json.load(f)
print("# Generating plots ...")
result_table = []
for gt_file_id, pred_info in dice_results.items():
    ensemble_data = pred_info["ensemble"]
    model_predictions = pred_info["models"]
    for pred_id, model_predictions in pred_info.items():
        for seg_id, class_dices in pred_info.items():
            for class_id in range(0,len(class_dices)):
                class_dice=class_dices[class_id]
                result_table.append([
                    file_id,
                    model_id_ensemble,
                    label_key,
                    dice_result
                ])

df_data = pd.DataFrame(result_table, columns=['Series', 'Model', 'Label', 'Dice'])
labels = df_data['Label'].unique()

# for label in labels:
#     df_filtered = df_data[df_data.Label == label]
#     self.create_plots(data_table=df_filtered, table_name=label, result_dir=result_dir)
# self.create_plots(data_table=df_data, table_name="all", result_dir=result_dir)

# print("# DONE #")
