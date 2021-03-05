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


def predict(model, input_folder, output_folder, folds, save_npz, num_threads_preprocessing, num_threads_nifti_save, part_id, num_parts, tta, mixed_precision, overwrite_existing, mode, overwrite_all_in_gpu, step_size, checkpoint_name, lowres_segmentations=None):
    global task, task_body_part, task_targets, task_protocols
    print(f"#")
    print(f"# Start prediction....")
    print(f"# model:      {model}")
    print(f"# folds:      {folds}")

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
    assert len(nifti_files) == 1

    nib_img = nib.load(nifti_files[0])
    # x, y, z = img.shape
    # print(f"# Dimensions: {[x, y, z]}")

    nii_array = nib_img.get_fdata().astype(int)
    nifti_labels = list(np.unique(nii_array))

    print(f"# Task-targets:     {task_targets}")
    print(f"# SEG NIFTI Labels: {nifti_labels}")
    seg_info_json = {}
    seg_info_json["task_id"] = task
    seg_info_json["task_body_part"] = task_body_part
    seg_info_json["task_protocols"] = task_protocols
    seg_info_json["task_targets"] = task
    seg_info_json["algorithm"] = task.lower()

    if 0 in nifti_labels:
        nifti_labels.remove(0)
    else:
        print("#")
        print(f"# Couldn't find a 'Clear Label' 0 in NIFTI: {nifti_files[0]}")
        print("#")
        exit(1)

    if len(nifti_labels) == 0:
        print("##################################################### ")
        print("#")
        print("# No segmentation was found in result-NIFTI-file!")
        print(f"# NIFTI-file {nifti_files[0]}")
        print("# ABORT")
        print("#")
        print("##################################################### ")
        exit(1)
    labels_found = []
    for label_bin in nifti_labels:
        labels_found.append({
            "label_name": str(task_targets[label_bin]),
            "label_int": label_bin
        })

    seg_info_json["seg_info"] = labels_found
    seg_json_path = join(output_folder, 'seg_info.json')
    print(f"# Writing seg_info: {seg_json_path}")
    with open(seg_json_path, 'w') as outfile:
        json.dump(seg_info_json, outfile, sort_keys=True, indent=4, default=str)
    print("#")
    print("##################################################### ")


def create_dataset(search_dir):
    global batch_dataset, operator_in_dir, input_modality_dirs, workflow_dir

    input_data_dir = join('/', workflow_dir, "nnunet-input-data")
    if batch_dataset:
        batch_folders = [f for f in glob(join('/', workflow_dir, "nnunet-cohort", '*'))]
        for batch_element_dir in batch_folders:
            input_count = 0
            for input_modality in input_modality_dirs:
                nifti_dir = join(batch_element_dir, input_modality, "*.nii.gz")
                print(f"# Searching NIFTIs at {nifti_dir}.")
                niftis_found = glob(nifti_dir, recursive=True)

                for nifti in niftis_found:
                    target_filename = join(input_data_dir, basename(nifti).replace(".nii.gz", f"_{input_count:04d}.nii.gz"))
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
    else:
        input_count = 0
        input_data_dir = join(search_dir, "nnunet-input-data")
        for input_modality in input_modality_dirs:
            nifti_dir = join(search_dir, input_modality, "*.nii.gz")
            print(f"# Searching NIFTIs at {nifti_dir}.")
            niftis_found = glob(nifti_dir, recursive=True)

            for nifti in niftis_found:
                target_filename = join(input_data_dir, basename(nifti).replace(".nii.gz", f"_{input_count:04d}.nii.gz"))
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
    global workflow_dir, task, models_dir, train_network, batch_name
    model_paths = []
    if models_dir == "/models":
        model_path = join(models_dir, "nnUNet", train_network)
        print(f"# Default models dir: {model_path} -> continue")
        model_paths.append(model_path)
    else:
        model_path = join(batch_element_dir, models_dir, train_network)
        batch_models_dir = join('/', workflow_dir, models_dir, train_network)
        print(f"# Batch-element models dir: {model_path}")
        print(f"# Batch models dir: {batch_models_dir}")
        if exists(model_path):
            print("# Found batch-element models dir -> continue")
            model_paths.append(model_path)
        elif exists(batch_models_dir):
            print("# Found batch models dir -> continue")
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
            model_path = join(model_path, task)
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

        result_model_paths.append(model_path)
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

if task_targets[0] != "Clear Label":
    task_targets.insert(0, "Clear Label")

task_body_part = getenv("BODY_PART", "ENV NOT FOUND!")
task_protocols = getenv("PROTOCOLS", "ENV NOT FOUND!").split(",")

mode = getenv("MODE", "None")
mode = mode if mode.lower() != "none" else None
models_dir = getenv("MODELS_DIR", "None")
models_dir = models_dir if models_dir.lower() != "none" else "/models"
threads_preprocessing = getenv("INF_THREADS_PREP", "None")
threads_preprocessing = int(threads_preprocessing) if threads_preprocessing.lower() != "none" else 2
threads_nifiti = getenv("INF_THREADS_NIFTI", "None")
threads_nifiti = int(threads_nifiti) if threads_nifiti.lower() != "none" else 2
batch_dataset = getenv("INF_BATCH_DATASET", "False")
batch_dataset = True if batch_dataset.lower() == "true" else False
input_modality_dirs = getenv("INPUT_MODALITY_DIRS", "None")
input_modality_dirs = input_modality_dirs.split(",") if input_modality_dirs.lower() != "none" else None

workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
enable_softmax = getenv("INF_SOFTMAX", "False")
enable_softmax = True if enable_softmax.lower() == "true" else False

train_network = getenv("TRAIN_NETWORK", "None")
train_network = train_network if train_network.lower() != "none" else None
train_network_trainer = getenv("TRAIN_NETWORK_TRAINER", "None")
train_network_trainer = train_network_trainer if train_network_trainer.lower() != "none" else None

tta = False
mixed_precision = True
override_existing = True
inf_mode = "fast"
step_size = 0.5
overwrite_all_in_gpu = False
checkpoint_name = "model_final_checkpoint"
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
print(f"# models_dir: {models_dir}")
print(f"# batch_name:   {batch_name}")
print(f"# workflow_dir: {workflow_dir}")
print(f"# batch_dataset: {batch_dataset}")
print(f"# enable_softmax: {enable_softmax}")
print(f"# operator_in_dir: {operator_in_dir}")
print(f"# operator_out_dir: {operator_out_dir}")
print(f"# input_modality_dirs: {input_modality_dirs}")
print(f"# threads_nifiti: {threads_nifiti}")
print(f"# threads_preprocessing: {threads_preprocessing}")
print(f"# train_network: {train_network}")
print(f"# train_network_trainer: {train_network_trainer}")
print("#")
print("##################################################")
print("#")
print("# Starting processing on batch-element-level ...")
print("#")
print("##################################################")
print("#")

processed_count = 0
batch_folders = [f for f in glob(join('/', workflow_dir, batch_name, '*'))]
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

    for model in model_paths:
        if folds == None and exists(join(model, "all")):
            folds = "all"
        print(f"#")
        print(f"# Start prediction....")
        print(f"# model:      {model}")
        print(f"# folds:      {folds}")

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
            checkpoint_name=checkpoint_name
        )
        processed_count += 1
        print(f"# Prediction ok.")
        print(f"#")


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

        for model in model_paths:
            if folds == None and exists(join(model, "all")):
                folds = "all"
            print(f"#")
            print(f"# Start prediction....")
            print(f"# model:      {model}")
            print(f"# folds:      {folds}")

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
                checkpoint_name=checkpoint_name
            )
            processed_count += 1
            print(f"# Prediction ok.")
            print(f"#")

if processed_count == 0:
    print("#")
    print("##################################################")
    print("#")
    print("#################  ERROR  #######################")
    print("#")
    print("# ----> NO FILES HAVE BEEN PROCESSED!")
    print("#")
    print("##################################################")
    print("#")
    exit(1)
else:
    print("# DONE #")
