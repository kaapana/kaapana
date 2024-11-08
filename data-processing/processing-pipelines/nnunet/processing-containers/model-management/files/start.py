from glob import glob
from pathlib import Path
import zipfile
import os
from shutil import rmtree

from kaapanapy.logger import get_logger
from kaapanapy.helper import load_workflow_config

logger = get_logger(__name__)


def extract_file_to_model_dir(zip_path, models_dir):
    """
    Extract the archive at zip_path to the models_dir.
    """
    Path(models_dir).mkdir(parents=True, exist_ok=True)
    logger.info(f"Unzipping {zip_path} -> {models_dir}")
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(models_dir)
        return True, zip_path
    except Exception as e:
        logger.error("Could not extract model: {}".format(zip_path))
        logger.error("Target dir: {}".format(models_dir))
        logger.error("MSG: " + str(e))
        return False, zip_path


def install_tasks():
    # Counter to check if smth has been processed
    processed_count = 0
    input_file_extension = "*.zip"
    workflow_dir = os.getenv("WORKFLOW_DIR", "None")
    workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
    assert workflow_dir is not None

    batch_name = os.getenv("BATCH_NAME", "None")
    batch_name = batch_name if batch_name.lower() != "none" else None
    assert batch_name is not None

    operator_in_dir = os.getenv("OPERATOR_IN_DIR", "None")
    operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
    assert operator_in_dir is not None

    operator_out_dir = os.getenv("OPERATOR_OUT_DIR", "None")
    operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
    assert operator_out_dir is not None

    target_level = os.getenv("TARGET_LEVEL", "None")
    target_level = target_level if target_level.lower() != "none" else None
    assert target_level is not None

    logger.debug(f"target_level:     {target_level}")
    logger.debug(f"workflow_dir:     {workflow_dir}")
    logger.debug(f"batch_name:       {batch_name}")
    logger.debug(f"operator_in_dir:  {operator_in_dir}")
    logger.debug(f"operator_out_dir: {operator_out_dir}")

    # Loop for every batch-element (usually series)
    batch_folders = sorted(
        [f for f in glob(os.path.join("/", workflow_dir, batch_name, "*"))]
    )
    for batch_element_dir in batch_folders:

        logger.info(f"Processing batch-element {batch_element_dir}")
        element_input_dir = os.path.join(batch_element_dir, operator_in_dir)
        element_output_dir = os.path.join(batch_element_dir, operator_out_dir)

        # check if input dir present
        if not os.path.exists(element_input_dir):
            logger.warning.info(f"Input-dir: {element_input_dir} does not exists!")
            logger.warning.info("-> skipping")
            continue

        # creating output dir
        Path(element_output_dir).mkdir(parents=True, exist_ok=True)

        # creating output dir
        logger.debug("Search for model-zip-files...")
        if target_level == "default":
            models_dir = "/models/nnUNet"
        elif target_level == "batch":
            models_dir = os.path.join(workflow_dir, element_output_dir)
        elif target_level == "batch_element":
            models_dir = os.path.join(batch_element_dir, element_output_dir)
        else:
            logger.error(f"target_level: {target_level} not supported!")
            exit(1)

        input_files = glob(
            os.path.join(element_input_dir, input_file_extension), recursive=True
        )
        logger.info(f"Found {len(input_files)} input-files!")

        if len(input_files) == 0:
            logger.error("No zip-files could be found on batch-element-level")
            exit(1)
        elif len(input_files) != 1:
            logger.error("More than one zip-files were found -> unexpected -> abort.")
            exit(1)

        # Single process:
        # Loop for every input-file found with extension 'input_file_extension'
        for input_file in input_files:
            success, input_file = extract_file_to_model_dir(
                zip_path=input_file, models_dir=models_dir
            )
            if not success:
                exit(1)
            else:
                processed_count += 1

    if processed_count == 0:
        logger.error("----> NO FILES HAVE BEEN PROCESSED!")
        exit(1)
    else:
        logger.info(f"----> {processed_count} FILES HAVE BEEN PROCESSED!")
        logger.info("Successfully extracted model into model-dir.")


def uninstall_tasks(models_dir="/models/nnUNet"):
    """
    Remove the directory corresponding all tasks in 'uninstall_tasks' in the workflow_form of the workflow_config.
    The directory that will be removed is generated as <models_dir>/<dataset_directory>/<model_directory>
    If the <dataset_directory> is empty after the <model_directory> was removed it will also be removed.

    Example:
        uninstall_tasks = ['Dataset451_10.135.76.131_061124-144541---nnUNetTrainer__nnUNetResEncUNetMPlans__3d_fullres']
        Path of removed directory:
        /models/nnUNet/Dataset451_10.135.76.131_061124-144541/nnUNetTrainer__nnUNetResEncUNetMPlans__3d_fullres
    """
    workflow_config = load_workflow_config()
    tasks_to_uninstall = workflow_config.get("workflow_form").get("uninstall_tasks")

    logger.info(f"tasks_to_uninstall:   {tasks_to_uninstall}")
    logger.info("Starting processing on BATCH-ELEMENT-level ...")
    for uninstall_task in tasks_to_uninstall:
        logger.info(f"Un-installing TASK: {uninstall_task}")

        dataset_directory_name, model_directory_name = tuple(
            uninstall_task.split("---")
        )
        dataset_path = Path(os.path.join(models_dir, dataset_directory_name))
        task_path = Path(
            os.path.join(models_dir, dataset_directory_name, model_directory_name)
        )

        assert task_path.is_dir()
        logger.info(f"Recursively remove {task_path=}")
        rmtree(task_path)

        try:
            dataset_path.rmdir()
            logger.info(f"Recursively remove {dataset_path=}")
        except OSError as e:
            if e.errno == 39:  ### Directory not empty error
                pass
            logger.error(f"Tried to remove the directory {dataset_path=}")
            raise e

        logger.info(f"{uninstall_task} successfully uninstalled!.")


if __name__ == "__main__":
    action = os.getenv("ACTION")

    if action == "install":
        install_tasks()
    elif action == "uninstall":
        uninstall_tasks()
    else:
        raise ValueError(
            f"{action=} not supported! Must be one of ['install','uninstall']"
        )
