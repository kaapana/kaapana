from os import getenv
from os.path import join, exists, dirname, basename, normpath
from glob import glob
from pathlib import Path
import zipfile
import os
from shutil import rmtree

# Counter to check if smth has been processed
processed_count = 0
target_level = None


# Process smth
def process_input_file(zip_path, models_dir):
    global processed_count

    Path(models_dir).mkdir(parents=True, exist_ok=True)

    print(f"# Unzipping {zip_path} -> {models_dir}")
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(models_dir)
        processed_count += 1
        return True, zip_path

    except Exception as e:
        print("")
        print("")
        print("")
        print("")
        print("Could not extract model: {}".format(zip_path))
        print("Target dir: {}".format(models_dir))
        print("Abort.")
        print("MSG: " + str(e))
        print("")
        print("")
        print("")
        print("")
        return False, zip_path


if __name__ == "__main__":
    workflow_dir = getenv("WORKFLOW_DIR", "None")
    workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
    assert workflow_dir is not None

    batch_name = getenv("BATCH_NAME", "None")
    batch_name = batch_name if batch_name.lower() != "none" else None
    assert batch_name is not None

    operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
    operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
    assert operator_in_dir is not None

    operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
    operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
    assert operator_out_dir is not None

    uninstall_task = getenv("UNINSTALL_TASK", "None")
    uninstall_task = uninstall_task if uninstall_task.lower() != "none" else None
    assert uninstall_task is not None

    target_level = getenv("TARGET_LEVEL", "None")
    target_level = target_level if target_level.lower() != "none" else None
    assert target_level is not None

    # File-extension to search for in the input-dir
    input_file_extension = "*.zip"

    print("##################################################")
    print("#")
    print("# Starting operator xyz:")
    print("#")
    print(f"# workflow_dir:     {workflow_dir}")
    print(f"# batch_name:       {batch_name}")
    print(f"# operator_in_dir:  {operator_in_dir}")
    print(f"# operator_out_dir: {operator_out_dir}")
    print(f"# target_level:     {target_level}")
    print(f"# uninstall_task:   {uninstall_task}")
    print("#")
    print("##################################################")
    print("#")
    print("# Starting processing on BATCH-ELEMENT-level ...")
    print("#")
    print("##################################################")
    print("#")
    print("#")

    if uninstall_task != "":
        models_dir = "/models/nnUNet"
        print(f"Un-installing TASK: {uninstall_task}")
        installed_models = [
            basename(normpath(f.path)) for f in os.scandir(models_dir) if f.is_dir()
        ]

        for installed_model in installed_models:
            model_path = join(models_dir, installed_model)
            installed_tasks_dirs = [
                basename(normpath(f.path)) for f in os.scandir(model_path) if f.is_dir()
            ]
            for installed_task in installed_tasks_dirs:
                if installed_task.lower() == uninstall_task.lower():
                    task_path = join(models_dir, installed_model, installed_task)
                    print(f"Removing: {task_path}")
                    rmtree(task_path)

    # Loop for every batch-element (usually series)
    batch_folders = sorted([f for f in glob(join("/", workflow_dir, batch_name, "*"))])
    for batch_element_dir in batch_folders:
        print("#")
        print(f"# Processing batch-element {batch_element_dir}")
        print("#")
        element_input_dir = join(batch_element_dir, operator_in_dir)
        element_output_dir = join(batch_element_dir, operator_out_dir)

        # check if input dir present
        if not exists(element_input_dir):
            print("#")
            print(f"# Input-dir: {element_input_dir} does not exists!")
            print("# -> skipping")
            print("#")
            continue

        # creating output dir
        Path(element_output_dir).mkdir(parents=True, exist_ok=True)

        # creating output dir
        print("------------------------------------")
        print("# Search for model-zip-files...")
        print("------------------------------------")
        if target_level == "default":
            models_dir = "/models/nnUNet"
        elif target_level == "batch":
            models_dir = join(workflow_dir, element_output_dir)
        elif target_level == "batch_element":
            models_dir = join(batch_element_dir, element_output_dir)
        else:
            print(f"#")
            print(f"# ERROR")
            print(f"#")
            print(f"# target_level: {target_level} not supported!")
            print(f"#")
            exit(1)

        input_files = glob(
            join(element_input_dir, input_file_extension), recursive=True
        )
        print(f"# Found {len(input_files)} input-files!")

        if len(input_files) == 0:
            print("# No zip-files could be found on batch-element-level")
            exit(1)
        elif len(input_files) != 1:
            print("# More than one zip-files were found -> unexpected -> abort.")
            exit(1)

        # Single process:
        # Loop for every input-file found with extension 'input_file_extension'
        for input_file in input_files:
            success, input_file = process_input_file(
                zip_path=input_file, models_dir=models_dir
            )
            if not success:
                exit(1)

    print("#")
    print("##################################################")
    print("#")
    print("# BATCH-ELEMENT-level processing done.")
    print("#")
    print("##################################################")
    print("#")

    if processed_count == 0:
        print("##################################################")
        print("#")
        print("# -> No files have been processed so far!")
        print("#")
        print("# Starting processing on BATCH-LEVEL ...")
        print("#")
        print("##################################################")
        print("##################################################")
        print("##################################################")
        print("#")
        print("# -> not supported yet!")
        print("#")
        print("#")
        print("##################################################")
        print("##################################################")
        print("##################################################")

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
        print("# ✓ successfully extracted model into model-dir.")
        print("#")
        print("# DONE")
