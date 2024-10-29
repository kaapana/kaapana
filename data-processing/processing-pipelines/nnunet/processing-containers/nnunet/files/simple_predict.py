# nnUNet imports
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

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


def create_dataset(search_dir):
    """
    Prepares a dataset of medical imaging files in NIfTI (.nii.gz) format for inference by organizing and copying/moving
    files from various input modality directories to a target directory. The function either processes batch datasets from a
    predefined workflow directory or processes individual input modalities directly from the provided search directory.

    Parameters:
    -----------
    search_dir : str
        Path to the directory where input modality directories are located when not using a batch dataset.

    Returns:
    --------
    tuple : (str, int)
        - str : Path to the target directory where processed NIfTI files are stored.
        - int : Count of .nii.gz files in the target directory after processing.

    Global Variables:
    -----------------
    batch_dataset : bool
        Flag indicating whether to process data as a batch dataset or from individual modality directories in search_dir.
    operator_in_dir : str
        Directory path for the operator, used within the processing workflow.
    input_modality_dirs : list
        List of directory names corresponding to input modalities to be searched for NIfTI files.
    workflow_dir : str
        Directory path for the overall workflow, used to determine paths for input and output data.
    copy_target_data : bool
        Flag indicating whether files should be copied (True) or moved (False) to the target directory.

    Notes:
    ------
    - The function checks if files in the target directory already exist to avoid duplicate processing.
    - The target filenames are suffixed with a zero-padded index (e.g., "_0000.nii.gz") to ensure uniqueness.
    - Prints status messages for each file search, copy, or move operation.

    Example Usage:
    --------------
    >>> input_data_dir, input_count = create_dataset('/path/to/search_dir')
    """

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
    """
    Identifies and verifies model paths and checkpoint files for nnUNet models, depending on the Kaapana workflow in which the function
    is called (either `nnunet-predict` or `nnunet-ensemble`). It retrieves task and model information from the directory structure,
    ensuring a valid model path with a final or latest checkpoint is found.

    Parameters:
    -----------
    batch_element_dir : str
        Path to the directory containing batch elements for model inference or training.

    Returns:
    --------
    list of tuples : [(str, str)]
        A list of tuples, each containing:
        - str : Valid model path identified for the specified task and model.
        - str : Checkpoint name (e.g., 'checkpoint_final' or 'checkpoint_latest') found within the model path.

    Global Variables:
    -----------------
    workflow_dir : str
        Path to the main workflow directory, used to build paths for models and tasks.
    task : str
        Name of the nnUNet task, used to identify the model path.
    models_dir : str
        Directory where models are stored, either in a standard location or within the batch directory.
    model_arch : str
        Name of the model architecture (e.g., nnUNetTrainerV2), used to locate the correct model.
    batch_name : str
        Name of the current batch, used within directory paths as needed.
    copy_target_data : bool
        Flag indicating whether to copy or move data to the target directory.

    Notes:
    ------
    - If `task` includes a double dash ("---"), it is split into task and model name components.
    - In the absence of `task` and `modelname` details, they are inferred from `checkpoint_final.pth` file paths.
    - If no valid model or checkpoint path is identified, the function exits with an error message.
    - Prints status messages detailing the paths and checkpoint statuses for debugging purposes.

    Example Usage:
    --------------
    >>> model_paths = get_model_paths('/path/to/batch_element_dir')
    """

    global workflow_dir, task, models_dir, model_arch, batch_name

    if task and "---" in task:
        # format if called from nnunet-predict
        task_n_modelname = task.split("---")
        task = task_n_modelname[0]
        modelname = task_n_modelname[1]
    else:
        # retrieve infromation if called from nnunet-ensemble
        checkpoint_file = glob(
            f"{batch_element_dir}/**/checkpoint_final.pth", recursive=True
        )[0]
        checkpoint_file_substring = checkpoint_file.split("/")
        task = next(
            (
                element
                for element in checkpoint_file_substring
                if element.startswith("Dataset")
            ),
            None,
        )
        modelname = next(
            (
                element
                for element in checkpoint_file_substring
                if element.startswith("nnUNetTrainer")
            ),
            None,
        )

    model_paths = []
    if models_dir == "/models":
        # that's the case if called from nnunet-predict workflow
        model_path = join(models_dir, "nnUNet", task, modelname)
        print(f"# Default models dir: {model_path} -> continue")
        model_paths.append(model_path)
    else:
        # that's the case if called from nnunet-ensemble workflow
        model_path = join(batch_element_dir, models_dir, task, modelname)
        batch_models_dir = join("/", workflow_dir, models_dir, task, modelname)
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
            # model_path = join(model_path, modelname)
            print(f"# Final model_path: {model_path}")

        assert exists(model_path)
        fold = [f.name for f in os.scandir(model_path) if f.is_dir()]
        if len(fold) == 1:
            model_path = join(model_path, fold[0])
            print(f"# Fold indenified: {fold[0]}")
        else:
            print("# Fold could not be identified...")
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
                    join(model_path, "**", "checkpoint_final.pth"),
                    recursive=True,
                )
            )
            > 0
        ):
            checkpoint_name = "checkpoint_final"
        elif (
            len(glob(join(model_path, "**", "checkpoint_latest.pth"), recursive=True))
            > 0
        ):
            checkpoint_name = "checkpoint_latest"
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


def write_seg_info(task, target_dir, dataset_info_dir):
    """
    Generates and writes a `seg_info.json` file containing segmentation label information and model metadata based on
    details from a dataset configuration file.

    Parameters:
    -----------
    task : str
        Identifier for the nnUNet task, typically includes the dataset and model name.
    target_dir : str
        Path to the directory where `seg_info.json` should be saved.
    dataset_info_dir : str
        Path to the directory containing `dataset.json` with segmentation labels and other dataset information.

    Returns:
    --------
    None
        Outputs `seg_info.json` to the specified `target_dir`.

    Notes:
    ------
    - Reads label information from `dataset.json`, which should have a `labels` dictionary with label names and values.
    - Extracts the `task_id` and `algorithm` fields from the `task` path, including dataset and model identifiers.
    - Prints the generated `seg_info` content to the console for verification.

    Example Usage:
    --------------
    >>> write_seg_info("Dataset001_nnUNetTrainerV2", "/output/path", "/input/dataset_info_dir")
    """

    print("# Writing seg_info.json ...")

    # get seg_info content form dataset.json
    # seg_info_path = Path(target_dir).parent / operator_in_dir
    with open(os.path.join(dataset_info_dir, "dataset.json"), "r") as file:
        dataset_dict = json.load(file)

    seg_info_list = [
        {"label_name": key, "label_int": str(value)}
        for key, value in dataset_dict["labels"].items()
    ]
    seg_info = {"seg_info": seg_info_list}

    task_substrings = str(task).split("/")
    seg_info["task_id"] = next(
        (element for element in task_substrings if element.startswith("Dataset")), None
    )
    algo_id = next(
        (element for element in task_substrings if element.startswith("nnUNetTrainer")),
        None,
    )
    seg_info["algorithm"] = seg_info["task_id"] + algo_id

    json_path = os.path.join(target_dir, "seg_info.json")

    with open(json_path, "w") as outfile:
        json.dump(seg_info, outfile, sort_keys=True, indent=4)

    print(json.dumps(seg_info, indent=4, sort_keys=True))
    print("#")


def predict(
    input_data_dir,
    element_output_dir,
    model,
    folds="all",
    checkpoint_name="model_final_checkpoint",
    enable_softmax="False",
):
    """
    Runs segmentation predictions using nnUNet's predictor for medical images, initializing the network from a trained
    model and saving predictions to the specified output directory.

    Parameters:
    -----------
    input_data_dir : str
        Directory containing input data files to be processed by the model.
    element_output_dir : str
        Directory where the model's predictions will be saved.
    model : str
        Path to the trained model directory.
    folds : str or list, default "all"
        Folds to use during prediction; "all" uses all available folds, or specify a list of fold indices.
    checkpoint_name : str, default "model_final_checkpoint"
        Name of the checkpoint file to load for the model (without the `.pth` extension).
    enable_softmax : str, default "False"
        Whether to save probability maps by applying softmax on predictions (set to "True" to enable).

    Returns:
    --------
    None
        Predictions are saved to `element_output_dir`.

    Notes:
    ------
    - Initializes the nnUNetPredictor with settings for tiling, mirroring, and device usage.
    - Prepares the model by loading the specified checkpoint and folds.
    - `predict_from_files` is called with configurations for saving probabilities, managing parallel processing,
      and specifying parts if applicable.

    Example Usage:
    --------------
    >>> predict("/path/to/input_data", "/path/to/output_dir", "/path/to/model", folds="all", enable_softmax="True")
    """

    ### from nnU-Net V2 docs
    # source: https://github.com/MIC-DKFZ/nnUNet/tree/master/nnunetv2/inference#recommended-nnu-net-default-predict-from-source-files
    # instantiate the nnUNetPredictor
    predictor = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        use_mirroring=True,
        perform_everything_on_device=True,
        device=torch.device("cuda", 0),
        verbose=False,
        verbose_preprocessing=False,
        allow_tqdm=True,
    )
    # initializes the network architecture, loads the checkpoint
    predictor.initialize_from_trained_model_folder(
        model,
        use_folds=folds,
        checkpoint_name=checkpoint_name + ".pth",
    )
    # give input and output folders
    predictor.predict_from_files(
        input_data_dir,
        element_output_dir,
        save_probabilities=enable_softmax,
        overwrite=False,
        num_processes_preprocessing=2,
        num_processes_segmentation_export=2,
        folder_with_segs_from_prev_stage=None,
        num_parts=1,
        part_id=0,
    )


folds = getenv("TRAIN_FOLD", "None")
folds = folds if folds.lower() != "none" else None
folds = folds.split(",") if folds != None else None

batch_name = getenv("BATCH_NAME", "None")
batch_name = batch_name if batch_name.lower() != "none" else None

task = getenv("TASK_IDS", "None")
task = task if task.lower() != "none" else None

task_targets = os.getenv("TARGETS", "None")
task_targets = task_targets.split(",") if task_targets.lower() != "none" else None

if task_targets != None and task_targets[0] != "background":
    task_targets.insert(0, "background")

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


if __name__ == "__main__":
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

        # e.g.: /models/nnUNet/Dataset579_10.135.76.130_010824-0934/nnUNetTrainer__nnUNetResEncUNetMPlans__3d_lowres/fold_all
        model_paths = get_model_paths(batch_element_dir=batch_element_dir)
        for model, checkpoint_name in model_paths:
            if folds == None and "fold_all" in model or folds == "all":
                folds = "all"
                model = Path(model).parent
            print("#")
            print("##################################################")
            print("#                                                #")
            print(f"# Start prediction....                           #")
            print("#                                                #")
            print("##################################################")
            print("#")
            print(f"# model: {model}")
            print("#")

            # predict via nnU-Net's predict function
            predict(
                input_data_dir,
                element_output_dir,
                model,
                folds,
                checkpoint_name,
                enable_softmax,
            )
            # write corresponding seg_info.json
            write_seg_info(model, element_output_dir, dataset_info_dir=model)

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
                if folds == None and "fold_all" in model:
                    folds = "all"
                    model = Path(model).parent

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

                # predict via nnU-Net's predict function
                predict(
                    input_data_dir,
                    output_dir,
                    model,
                    folds,
                    checkpoint_name,
                    enable_softmax,
                )
                # write corresponding seg_info.json
                write_seg_info(model, task_targets, output_dir)

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
