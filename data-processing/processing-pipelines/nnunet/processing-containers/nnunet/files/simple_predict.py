from nnunet.inference.predict import predict_from_folder
from pathlib import Path
import os
import json
import nibabel as nib
import numpy as np
from os import getenv, replace
from os.path import join, dirname, basename, exists
from glob import glob
import torch
import shutil


def get_model_targets(model_dir, targets):
    print(f"# Searching for dataset.json @: {model_dir}")
    dataset_json = glob(join(model_dir, "**", "dataset.json"), recursive=True)
    if len(dataset_json) != 0:
        print(f"# Loading dataset.json: {dataset_json[0]}")
        with open(dataset_json[0]) as f:
            dataset_json = json.load(f)
        return dataset_json

    return None


def predict(
    model,
    input_folder,
    output_folder,
    folds,
    save_npz,
    num_threads_preprocessing,
    num_threads_nifti_save,
    part_id,
    num_parts,
    tta,
    mixed_precision,
    overwrite_existing,
    mode,
    overwrite_all_in_gpu,
    step_size,
    checkpoint_name,
    lowres_segmentations=None,
):
    global task, task_body_part, task_targets, task_protocols, inf_seg_filter, remove_if_empty

    target_labels = {}
    if task is None:
        print("# Loading model-info-json ...")
        model_info = get_model_targets(model_dir=model, targets=task_targets)
        assert model_info is not None and "labels" in model_info
        print("# model_info:")
        print("# ")
        print(json.dumps(model_info, indent=4, sort_keys=True, default=str))
        print("# ")
        local_task = model_info["name"]
        target_labels = model_info["labels"]
        local_task_protocols = (
            ",".join(model_info["modality"].values())
            if "modality" in model_info
            else "N/A"
        )

    else:
        print("# Using env configuration ...")
        print("# ")
        local_task = task
        local_task_protocols = task_protocols
        assert task_targets is not None
        for index in range(0, len(task_targets)):
            target_labels[index] = task_targets[index]

    print(f"#")
    print(f"# Start prediction....")
    print(f"# task:       {local_task}")
    print(f"# model:      {model}")
    print(f"# folds:      {folds}")
    print(f"#")
    print(f"# target_labels:  {target_labels}")
    print(f"# task_protocols: {local_task_protocols}")
    print(f"#")

    Path(element_output_dir).mkdir(parents=True, exist_ok=True)
    predict_from_folder(
        model=model,
        input_folder=input_folder,
        output_folder=output_folder,
        folds=folds,
        save_npz=save_npz,
        num_threads_preprocessing=num_threads_preprocessing,
        num_threads_nifti_save=num_threads_nifti_save,
        part_id=part_id,
        num_parts=num_parts,
        tta=tta,
        mixed_precision=mixed_precision,
        overwrite_existing=overwrite_existing,
        mode=mode,
        overwrite_all_in_gpu=overwrite_all_in_gpu,
        step_size=step_size,
        checkpoint_name=checkpoint_name,
        lowres_segmentations=lowres_segmentations,
    )
    torch.cuda.empty_cache()
    print("#")
    print(f"# Checking NIFTI output for {output_folder}")
    print("#")
    nifti_files = sorted(glob(join(output_folder, "*.nii*"), recursive=False))
    assert len(nifti_files) > 0

    labels_found = []
    for int_encoding, label_key in target_labels.items():
        labels_found.append({"label_name": label_key, "label_int": str(int_encoding)})

    if remove_if_empty:
        for nifti_file in nifti_files:
            print(f"# Loading result NIFTI: {nifti_file}")
            labels_file = list(np.unique(nib.load(nifti_file).get_fdata().astype(int)))
            if len(labels_file) == 1:
                print("#")
                print("#")
                print("#")
                print("#")
                print("#")
                print("#")
                print("##################################################### ")
                print("#")
                print("# No segmentation was found in result-NIFTI-file!")
                print(f"# deleting NIFTI-file {nifti_files[0]}")
                print("#")
                print("##################################################### ")
                print("#")
                print("#")
                print("#")
                print("#")
                print("#")
                print("#")
                print("#")
                os.remove(nifti_file)

    seg_info_json = {}
    seg_info_json["task_id"] = (
        local_task if local_task != None else model.split("/")[-2]
    )
    seg_info_json["task_body_part"] = task_body_part
    seg_info_json["task_protocols"] = local_task_protocols
    seg_info_json["task_targets"] = task
    seg_info_json["algorithm"] = (
        task.lower() if task != None else model.split("/")[-2].lower()
    )

    seg_info_json["seg_info"] = labels_found
    seg_json_path = join(output_folder, "seg_info.json")
    print(f"# Writing seg_info: {seg_json_path}")
    with open(seg_json_path, "w") as outfile:
        json.dump(seg_info_json, outfile, sort_keys=True, indent=4, default=str)
    print("#")
    print("##################################################### ")


def create_dataset(search_dir):
    global batch_dataset, operator_in_dir, input_modality_dirs, workflow_dir

    input_data_dir = join("/", workflow_dir, "nnunet-input-data")
    Path(input_data_dir).mkdir(parents=True, exist_ok=True)

    if batch_dataset:
        batch_folders = sorted(
            [f for f in glob(join("/", workflow_dir, "nnunet-dataset", "*"))]
        )
        for batch_element_dir in batch_folders:
            input_count = 0
            for input_modality in input_modality_dirs:
                nifti_dir = join(batch_element_dir, input_modality, "*.nii.gz")
                print(f"# Searching NIFTIs at {nifti_dir}.")
                niftis_found = glob(nifti_dir, recursive=True)

                for nifti in niftis_found:
                    target_filename = join(
                        input_data_dir,
                        basename(nifti).replace(
                            ".nii.gz", f"_{input_count:04d}.nii.gz"
                        ),
                    )
                    if exists(target_filename):
                        print(f"# target_filename: {target_filename}")
                        print(f"# Target input-data already exists -> skipping")
                        continue

                    if copy_target_data:
                        print(f"# Copy file {nifti} to {target_filename}")
                        shutil.copy2(nifti, target_filename)
                    else:
                        print(f"# Moving file {nifti} to {target_filename}")
                        shutil.move(nifti, target_filename)
                    input_count += 1
    else:
        input_count = 0
        input_data_dir = join(search_dir, "nnunet-input-data")
        for input_modality in input_modality_dirs:
            nifti_dir = join(search_dir, input_modality, "*.nii.gz")
            print(f"# Searching NIFTIs at {nifti_dir}.")
            niftis_found = glob(nifti_dir, recursive=True)

            for nifti in niftis_found:
                target_filename = join(
                    input_data_dir,
                    basename(nifti).replace(".nii.gz", f"_{input_count:04d}.nii.gz"),
                )
                if exists(target_filename):
                    print(f"# Target input-data already exists -> skipping")
                    continue

                Path(input_data_dir).mkdir(parents=True, exist_ok=True)
                if copy_target_data:
                    print(f"# Copy file {nifti} to {target_filename}")
                    shutil.copy2(nifti, target_filename)
                else:
                    print(f"# Moving file {nifti} to {target_filename}")
                    shutil.move(nifti, target_filename)
                input_count += 1

    input_count = len(glob(join(input_data_dir, "*.nii.gz"), recursive=True))

    return input_data_dir, input_count


def get_model_paths(batch_element_dir):
    global workflow_dir, task, models_dir, model_arch, batch_name
    model_paths = []
    if models_dir == "/models":
        model_path = join(models_dir, "nnUNet", model_arch)
        print(f"# Default models dir: {model_path} -> continue")
        model_paths.append(model_path)
    else:
        model_path = join(batch_element_dir, models_dir, model_arch)
        batch_models_dir = join("/", workflow_dir, models_dir, model_arch)
        print(f"# Batch-element models dir: {model_path}")
        print(f"# Batch models dir: {batch_models_dir}")
        if exists(model_path):
            print("# Found batch-element models dir -> continue")
            print(f"# model_path: {model_path}")
            model_paths.append(model_path)
        elif exists(batch_models_dir):
            print("# Found batch models dir -> continue")
            print(f"# model_path: {batch_models_dir}")
            model_paths.append(batch_models_dir)
        else:
            print("# Could not find models !")
            print("# ABORT !")
            exit(1)

    if len(model_paths) == 0:
        print("# No model-path identified ...")
        print("# ABORT !")
        exit(1)

    result_model_paths = []
    for model_path in model_paths:
        if task == None:
            print("# Task not set!")
            tasks = [f.name for f in os.scandir(model_path) if f.is_dir()]
            if len(tasks) == 1:
                task_idenified = tasks[0]
                print(f"# Task idenified: {task_idenified}")
            else:
                print("# Task could not be identified...")
                print(f"# model_path:  {model_path}")
                print(f"# Tasks found: {task_idenified}")
                print("# ABORT !")
                exit(1)
            model_path = join(model_path, task_idenified)
        else:
            print(f"# Task: {task}")
            model_path = join(model_path, task)
            print(f"# Final model_path: {model_path}")

        assert exists(model_path)
        trainer = [f.name for f in os.scandir(model_path) if f.is_dir()]
        if len(trainer) == 1:
            model_path = join(model_path, trainer[0])
            print(f"# Trainer indenified: {trainer[0]}")
        else:
            print("# Trainer could not be identified...")
            print("# ABORT !")
            exit(1)

        if not exists(model_path):
            print("#")
            print("##################################################")
            print("#")
            print(f"# Error - model_path: {model_path} does not exist!")
            print("#")
            print("# ABORT")
            print("#")
            print("##################################################")
            print("#")
            exit(1)

        if (
            len(
                glob(
                    join(model_path, "**", "model_final_checkpoint.model.pkl"),
                    recursive=True,
                )
            )
            > 0
        ):
            checkpoint_name = "model_final_checkpoint"
        elif (
            len(glob(join(model_path, "**", "model_latest.model.pkl"), recursive=True))
            > 0
        ):
            checkpoint_name = "model_latest"
        else:
            print("#")
            print("##################################################")
            print("#")
            print(f"# Error - model_path: {model_path}")
            print("#")
            print(f"# Could not find any checkpoint!")
            print("#")
            print("# ABORT")
            print("#")
            print("##################################################")
            print("#")
            exit(1)

        print(f"# Found model_path:      {model_path}")
        print(f"# Found checkpoint_name: {checkpoint_name}")

        result_model_paths.append((model_path, checkpoint_name))
    return result_model_paths


# def write_seg_info(task, targets, target_dir):
#     print("# Writing seg_info.json ...")
#     seg_info = {"seg_info": targets}
#     seg_info["algorithm"] = task
#     json_path = os.path.join(target_dir, 'seg_info.json')

#     with open(json_path, 'w') as outfile:
#         json.dump(seg_info, outfile, sort_keys=True, indent=4)

#     print(json.dumps(seg_info, indent=4, sort_keys=True))
#     print("#")


folds = getenv("TRAIN_FOLD", "None")
folds = folds if folds.lower() != "none" else None
folds = folds.split(",") if folds != None else None

batch_name = getenv("BATCH_NAME", "None")
batch_name = batch_name if batch_name.lower() != "none" else None

task = getenv("TASK", "None")
task = task if task.lower() != "none" else None

task_targets = os.getenv("TARGETS", "None")
task_targets = task_targets.split(",") if task_targets.lower() != "none" else None

if task_targets != None and task_targets[0] != "Clear Label":
    task_targets.insert(0, "Clear Label")

task_body_part = getenv("BODY_PART", "N/A")
task_protocols = getenv("INPUT", "NOT FOUND!").split(",")

mode = getenv("MODE", "None")
mode = mode if mode.lower() != "none" else None
models_dir = getenv("MODELS_DIR", "None")
models_dir = models_dir if models_dir.lower() != "none" else "/models"
threads_preprocessing = getenv("INF_THREADS_PREP", "None")
threads_preprocessing = (
    int(threads_preprocessing) if threads_preprocessing.lower() != "none" else 2
)
threads_nifiti = getenv("INF_THREADS_NIFTI", "None")
threads_nifiti = int(threads_nifiti) if threads_nifiti.lower() != "none" else 2
batch_dataset = getenv("INF_BATCH_DATASET", "False")
batch_dataset = True if batch_dataset.lower() == "true" else False
input_modality_dirs = getenv("INPUT_MODALITY_DIRS", "None")
input_modality_dirs = (
    input_modality_dirs.split(",") if input_modality_dirs.lower() != "none" else None
)

workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
enable_softmax = getenv("INF_SOFTMAX", "False")
enable_softmax = True if enable_softmax.lower() == "true" else False

model_arch = getenv("MODEL", "None")
model_arch = model_arch if model_arch.lower() != "none" else None
train_network_trainer = getenv("TRAIN_NETWORK_TRAINER", "None")
train_network_trainer = (
    train_network_trainer if train_network_trainer.lower() != "none" else None
)

cuda_visible_devices = getenv("CUDA_VISIBLE_DEVICES", "None")
tta = getenv("TEST_TIME_AUGMENTATION", "None")
tta = True if tta.lower() == "true" else False

interpolation_order = getenv("INTERPOLATION_ORDER", "default")
mixed_precision = getenv("MIXED_PRECISION", "None")
mixed_precision = False if mixed_precision.lower() == "false" else True


remove_if_empty = getenv("INF_REMOVE_IF_EMPTY", "None")
remove_if_empty = True if remove_if_empty.lower() == "true" else False

inf_seg_filter = getenv("INF_SEG_FILTER", "None")
inf_seg_filter = inf_seg_filter.split(",") if inf_seg_filter.lower() != "none" else None

override_existing = True
inf_mode = "fast"
step_size = 0.5
overwrite_all_in_gpu = None
# overwrite_all_in_gpu = False
# checkpoint_name = "model_final_checkpoint"
part_id = 0
num_parts = 1

copy_target_data = True

if enable_softmax:
    inf_mode = "normal"

print("##################################################")
print("#")
print("# Starting nnUNet simple predict....")
print("#")
print(f"# task:  {task}")
print(f"# mode:  {mode}")
print(f"# folds: {folds}")
print("#")
print(f"# task_targets: {task_targets}")
print(f"# task_protocols: {task_protocols}")
print(f"# task_body_part: {task_body_part}")
print("#")
print(f"# models_dir: {models_dir}")
print(f"# batch_name:   {batch_name}")
print(f"# workflow_dir: {workflow_dir}")
print(f"# batch_dataset: {batch_dataset}")
print(f"# enable_softmax: {enable_softmax}")
print(f"# remove_if_empty: {remove_if_empty}")
print(f"# operator_in_dir: {operator_in_dir}")
print(f"# operator_out_dir: {operator_out_dir}")
print(f"# input_modality_dirs: {input_modality_dirs}")
print(f"# threads_nifiti:      {threads_nifiti}")
print(f"# threads_preprocessing: {threads_preprocessing}")
print(f"# model_arch:            {model_arch}")
print(f"# train_network_trainer: {train_network_trainer}")
print("#")
print(f"# tta:  {tta}")
print(f"# mixed_precision:       {mixed_precision}")
print(f"# INTERPOLATION_ORDER:   {interpolation_order}")
print(f"# cuda_visible_devices:  {cuda_visible_devices}")
print("#")
print("#")
print(f"# inf_seg_filter:  {inf_seg_filter}")
print("#")
print("##################################################")
print("#")
print("# Starting processing on batch-element-level ...")
print("#")
print("##################################################")
print("#")

processed_count = 0
batch_folders = sorted([f for f in glob(join("/", workflow_dir, batch_name, "*"))])
for batch_element_dir in batch_folders:
    input_data_dir, input_count = create_dataset(search_dir=batch_element_dir)
    if input_count == 0:
        print("#")
        print("##################################################")
        print("#")
        print("# No NIFTI files found on batch-element-level!")
        print("#")
        print("##################################################")
        print("#")
        break

    # element_input_dir = join(batch_element_dir, operator_in_dir)
    element_output_dir = join(batch_element_dir, operator_out_dir)

    # models/nnUNet/3d_lowres/Task003_Liver/nnUNetTrainerV2__nnUNetPlansv2.1/fold_1
    model_paths = get_model_paths(batch_element_dir=batch_element_dir)
    for model, checkpoint_name in model_paths:
        if folds == None and exists(join(model, "all")):
            folds = "all"
        print("#")
        print("##################################################")
        print("#                                                #")
        print(f"# Start prediction....                           #")
        print("#                                                #")
        print("##################################################")
        print("#")
        print(f"# model: {model}")
        print("#")

        predict(
            model=model,
            input_folder=input_data_dir,
            output_folder=element_output_dir,
            folds=folds,
            save_npz=enable_softmax,
            num_threads_preprocessing=threads_preprocessing,
            num_threads_nifti_save=threads_nifiti,
            lowres_segmentations=None,
            part_id=part_id,
            num_parts=num_parts,
            tta=tta,
            mixed_precision=mixed_precision,
            overwrite_existing=override_existing,
            mode=inf_mode,
            overwrite_all_in_gpu=overwrite_all_in_gpu,
            step_size=step_size,
            checkpoint_name=checkpoint_name,
        )
        processed_count += 1
        print("#")
        print("##################################################")
        print("#                                                #")
        print("#                 Prediction ok                  #")
        print("#                                                #")
        print("##################################################")
        print("#                                                #")
        print(f"# model: {model}")
        print("#")

    input_data_dir = join("/", workflow_dir, "nnunet-input-data")
    shutil.rmtree(input_data_dir, ignore_errors=True)

if processed_count == 0:
    print("##################################################")
    print("#")
    print("# Starting processing on batch-level ...")
    print("#")
    print("##################################################")
    input_data_dir, input_count = create_dataset(search_dir=workflow_dir)

    if input_count == 0:
        print("#")
        print("# No files on batch-level found -> continue")
        print("#")
    else:
        # element_input_dir = join(batch_element_dir, operator_in_dir)
        output_dir = join(workflow_dir, operator_out_dir)

        # models/nnUNet/3d_lowres/Task003_Liver/nnUNetTrainerV2__nnUNetPlansv2.1/fold_1
        model_paths = get_model_paths(batch_element_dir=workflow_dir)
        if folds == None and exists(join(model_paths, "all")):
            folds = "all"

        for model, checkpoint_name in model_paths:
            if folds == None and exists(join(model, "all")):
                folds = "all"
            print("#")
            print("##################################################")
            print("#                                                #")
            print(f"# Start prediction....                           #")
            print("#                                                #")
            print("##################################################")
            print("#")
            print(f"# model: {model}")
            print(f"# folds: {folds}")
            print("#")

            predict(
                model=model,
                input_folder=input_data_dir,
                output_folder=output_dir,
                folds=folds,
                save_npz=enable_softmax,
                num_threads_preprocessing=threads_preprocessing,
                num_threads_nifti_save=threads_nifiti,
                lowres_segmentations=None,
                part_id=part_id,
                num_parts=num_parts,
                tta=tta,
                mixed_precision=mixed_precision,
                overwrite_existing=override_existing,
                mode=inf_mode,
                overwrite_all_in_gpu=overwrite_all_in_gpu,
                step_size=step_size,
                checkpoint_name=checkpoint_name,
            )
            processed_count += 1
            print(f"# Prediction ok.")
            print(f"#")

    input_data_dir = join("/", workflow_dir, "nnunet-input-data")
    shutil.rmtree(input_data_dir, ignore_errors=True)

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
