import os
import shutil
import json
import itertools
from pathlib import Path
from os import getenv
from os.path import basename, join, exists
from glob import glob
from nnunet.inference.ensemble_predictions import merge

batch_name = getenv("BATCH_NAME", "None")
batch_name = batch_name if batch_name.lower() != "none" else None

workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None

operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None

operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None

threads_nifiti = getenv("INF_THREADS_NIFTI", "None")
threads_nifiti = int(threads_nifiti) if threads_nifiti.lower() != "none" else 2

pred_min_combination = getenv("PRED_MIN_COMBINATION", "None")
pred_min_combination = (
    int(pred_min_combination) if pred_min_combination.lower() != "none" else None
)

override = True
store_npz = True
postprocessing_file = None

global_seg_info = []


def check_seg_info(inference_dir):
    global global_seg_info
    print("#")
    print(f"# Checking seg info for {inference_dir} ...")
    seg_info_file = join(inference_dir, "seg_info.json")
    assert exists(seg_info_file)
    with open(seg_info_file) as f:
        new_seg_infos = json.load(f)

    assert "seg_info" in new_seg_infos
    new_dict = {}
    for new_seg_info in new_seg_infos["seg_info"]:
        new_label_key = new_seg_info["label_name"]
        new_label_encoding_str = new_seg_info["label_int"]
        new_dict[new_label_key] = new_label_encoding_str

    if len(global_seg_info) == 0:
        print("# Creating first inference_dir configuration...")
        global_seg_info.append(
            {
                "seg_file_path": seg_info_file,
                "inference_dirs": [inference_dir],
                "seg_info": new_dict,
            }
        )
    else:
        found = False
        for existing_entry in global_seg_info:
            if new_dict == existing_entry["seg_info"]:
                print("# Adding inference_dir to existing configuration...")
                existing_entry["inference_dirs"].append(inference_dir)
                found = True

        if not found:
            print("# Adding new inference_dir configuration...")
            global_seg_info.append(
                {
                    "seg_file_path": seg_info_file,
                    "inference_dirs": [inference_dir],
                    "seg_info": new_dict,
                }
            )

    print("#")


print("##################################################")
print("#")
print("# Starting nnUNet simple predict....")
print("#")
print(f"# override:            {override}")
print(f"# threads_nifiti:      {threads_nifiti}")
print(f"# operator_in_dir:     {operator_in_dir}")
print(f"# operator_out_dir:    {operator_out_dir}")
print(f"# postprocessing_file: {postprocessing_file}")
print("#")
print(f"# pred_min_combination: {pred_min_combination}")
print("#")
print("##################################################")
print("#")

processed_count = 0
batch_folders = sorted([f for f in glob(join("/", workflow_dir, batch_name, "*"))])
for batch_element_dir in batch_folders:
    element_input_dir = os.path.join(batch_element_dir, operator_in_dir)
    if exists(element_input_dir):
        if "skip" not in element_input_dir:
            check_seg_info(element_input_dir)
            print(f"#")
        else:
            print(f"# Skipping {element_input_dir} to the ensemble...")
            print(f"#")
    else:
        print(f"# Input-Dir {element_input_dir} not found! -> unexpected -> ABORT")
        print(f"#")
        exit(1)

assert len(global_seg_info) > 0

if len(global_seg_info) > 1:
    global_seg_info = sorted(
        global_seg_info, key=lambda k: len(k["inference_dirs"]), reverse=True
    )

    for skipped_models in global_seg_info[1:]:
        print("#")
        print("##################################################")
        print("#")
        print("#################  INFO  #######################")
        print("#")
        print("# ----> Skipped models because of different label configuration:")
        print("#")
        print(json.dumps(skipped_models, indent=4, sort_keys=True, default=str))
        print("#")
        print("##################################################")
        print("#")

print("#")

ensemble_dirs = global_seg_info[0]["inference_dirs"]
print(f"# ensemble_dirs: {ensemble_dirs}")
seg_file_path = global_seg_info[0]["seg_file_path"]
print(f"# seg_file_path: {seg_file_path}")

if len(ensemble_dirs) < 2:
    print("#")
    print("##################################################")
    print("#")
    print("#################  ERROR  #######################")
    print("#")
    print("# ----> Not enough valid model predictions!")
    print("#")
    print(f"# -> ensemble_dirs: {ensemble_dirs}")
    print("#")
    print("##################################################")
    print("#")
    exit(0)

pred_min_combination = (
    pred_min_combination if pred_min_combination is not None else len(ensemble_dirs)
)
pred_min_combination = 2 if pred_min_combination < 2 else pred_min_combination

model_combinations = []
for L in range(0, len(ensemble_dirs) + 1):
    for subset in itertools.combinations(ensemble_dirs, L):
        subset = list(subset)
        if len(subset) >= pred_min_combination:
            model_combinations.append(subset)

for combination_index in range(0, len(model_combinations)):
    model_combination = model_combinations[combination_index]
    combination_output_dir = os.path.join(
        "/", workflow_dir, operator_out_dir, f"combination_{combination_index}"
    )
    Path(combination_output_dir).mkdir(parents=True, exist_ok=True)
    print(f"#")
    print(f"# Evaluating combination: {combination_index}: {model_combination}")
    print(f"#")
    print(f"# combination_output_dir:    {combination_output_dir}")
    print(f"#")

    merge(
        folders=ensemble_dirs,
        output_folder=combination_output_dir,
        threads=threads_nifiti,
        postprocessing_file=postprocessing_file,
        store_npz=store_npz,
        override=override,
    )
    print(f"# COMBINATION {model_combination} DONE #")

print("#")
print("##################################################")
print("#")
print("# ALL COMBINATIONS DONE #")
print("#")
print("##################################################")
print("#")
print("# -> collecting ensemble files ...")
print("#")

final_target = join("/", workflow_dir, operator_out_dir)
combination_output_dirs = sorted(
    [f for f in glob(join("/", workflow_dir, operator_out_dir, "*"))]
)
for combination_output_dir in combination_output_dirs:
    print(
        f"# -> moving files from {basename(combination_output_dir)} to operator_out_dir"
    )

    assert "combination_" in combination_output_dir
    combination_id = int(combination_output_dir.split("_")[-1])
    combination_files = glob(join(combination_output_dir, "*"), recursive=False)
    for combination_file in combination_files:
        if ".nii.gz" in combination_file:
            extension = "nii.gz"
        else:
            extension = basename(combination_file).split(".")[-1]
        target_file_path = join(
            final_target,
            basename(combination_file).replace(
                f".{extension}", f"_combination_{combination_id}.{extension}"
            ),
        )
        print(f"# {basename(combination_file)} -> {basename(target_file_path)}")
        shutil.move(src=combination_file, dst=target_file_path)

    print(f"# -> deleting combination dir: {basename(combination_output_dir)}")
    shutil.rmtree(path=combination_output_dir)
    print(f"# done")

print("# Writing model_combinations.json")
print("# ")
print(json.dumps(model_combinations, indent=4, sort_keys=True, default=str))
print("# ")
with open(join(final_target, "model_combinations.json"), "w") as jsonData:
    json.dump(model_combinations, jsonData, indent=4, sort_keys=False, default=str)

shutil.copy(src=seg_file_path, dst=join(final_target, "ensemble_seg_info.json"))
print("#")
print("#")
print("##################################################")
print("#")
print("# ENSEMBLE DONE")
print("#")
print("##################################################")
print("#")
