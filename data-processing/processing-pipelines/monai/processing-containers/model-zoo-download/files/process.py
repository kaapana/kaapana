import os
from sys import stdout
import time
from datetime import datetime
from pathlib import Path
from shutil import rmtree
from os.path import join, basename, normpath
import logging
from monai.bundle import download


#logging.basicConfig(format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
logger.propagate = False
formatter = logging.Formatter('%(levelname)s - %(message)s')
console_handler = logging.StreamHandler(stdout)
console_handler.setFormatter(formatter)
logger.handlers.clear()
logger.addHandler(console_handler)


processed_count = 0
max_retries = 3
max_hours_since_creation = 3

workflow_dir = os.getenv('WORKFLOW_DIR', "data")
operator_dir = os.getenv("OPERATOR_OUT_DIR", "models")
models = os.getenv('MODELS', "NONE") ### "model1:vers1,model2:vers_model2"
models = None if models == "NONE" else models
mode = os.getenv('MODE', "install_pretrained")

output_dir = os.path.join('/', workflow_dir, operator_dir, "monai") ### https://docs.monai.io/en/latest/mb_specification.html

ALL_MODELS = [
            "spleen_ct_segmentation:0.3.1",
            ]

logger.info("# Starting GetModelOperator ...")
logger.info("#")
logger.info(f"# mode: {mode}")
logger.info(f"# model: {models}")
logger.info(f"# output_dir: {output_dir}")
logger.info(f"# workflow_dir: {workflow_dir}")
logger.info("#")
logger.info("#")

def check_dl_running(model_path_dl_running, model_path, wait=True):
    if os.path.isfile(model_path_dl_running):
        hours_since_creation = int((datetime.now() - datetime.fromtimestamp(os.path.getmtime(model_path_dl_running))).total_seconds()/3600)
        if hours_since_creation > max_hours_since_creation:
            logger.info("Download lock-file present! -> waiting until it is finished!")
            logger.info("File older than {} hours! -> removing and triggering download!".format(max_hours_since_creation))
            delete_file(model_path_dl_running)
            return False

        logger.info("Download already running -> waiting until it is finished!")
        while not os.path.isdir(model_path) and wait:
            time.sleep(15)
        return True
    else:
        logger.info("Download not running -> download!")
        return False


def delete_file(target_file):
    try:
        os.remove(target_file)
    except Exception as e:
        logger.info(e)
        pass


logger.info(f"-----     MODE: {mode}      -------")
if models is None:
    logger.info("No ENV 'MODELS' found!")
    logger.info("Abort.")
    exit(1)
elif models == "all":
    logger.info("Downloading all monai-models...")
    models_list = ALL_MODELS
    models = ",".join(models_list)
else:
    models_list = models.split(",")
logger.info("Models in the end: {}".format(models))

if mode == "install":
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    for model in models_list:
        try:
            model_name, version = model.split(":")
        except ValueError as e:
            logger.error("-----  No version specified!  ------")
            raise e

        model_subdir = model_name +"_v" + version
        model_path = os.path.join(output_dir, model_subdir)
        logger.info("Check if version already present: {}".format(model_subdir))
        logger.info("MODEL: {}".format(model_name))
        logger.info("VERSION: {}".format(version))

        if os.path.isdir(model_path):
            logger.info("Model {} found!".format(model_subdir))
            continue

        logger.info("Model not present: {}".format(model_subdir))

        model_path_dl_running = os.path.join(output_dir, "dl_{}.txt".format(model_subdir))
        wait = True if len(models_list) == 1 else False
        if check_dl_running(model_path_dl_running=model_path_dl_running, model_path=model_path, wait=wait):
            continue

        try_count = 0
        archive_name = f"{model_subdir}.zip"
        model_archive = os.path.join(output_dir, archive_name)
        while not os.path.isfile(model_archive) and try_count < max_retries:
            try_count += 1
            try:
                logger.info("set lock-file: {}".format(model_path_dl_running))
                Path(model_path_dl_running).touch()
                download(name=model_name, version=version, bundle_dir=model_path, progress=False)
            
            except Exception as e:
                logger.error("Could not download model: {}:{}".format(model_name,version))
                logger.error("Abort.")
                logger.error('MSG: ' + str(e))

        if try_count >= max_retries:
            logger.info("Max retries reached!")
            logger.info("Skipping...")
            delete_file(model_path_dl_running)
            continue

        delete_file(model_path_dl_running)


    logger.info("Check if all models are now present: {}".format(output_dir))
    success = True
    for model in models_list:
        try:
            model_name, version = model.split(":")
        except IndexError as e:
            logger.error("No version specified!")
            raise e
        model_path = os.path.join(output_dir, model_name +"_v" + version)

        if os.path.isdir(model_path):
            logger.info("Model {}:{} found!".format(model_name,version))
            continue
        else:
            success = False
            logger.error("Model NOT found: {}:{}".format(model_name, version))

    if not success:
        exit(1)

    logger.info("# ✓ All models successfully downloaded and extracted!")

elif mode == "uninstall":
    logger.info(f"Un-installing TASK: {models}")
    installed_models = [basename(normpath(f.path)) for f in os.scandir(output_dir) if f.is_dir()]

    for installed_model in installed_models:
        model_name, version = installed_model.split("_v")
        model = ":".join([model_name,version])

        if model.lower() in models.lower():
            monai_model_path = join(output_dir, installed_model)
            logger.info(f"Removing: {monai_model_path}")
            rmtree(monai_model_path)
else:
    logger.error(f"---- Mode not supported: {mode} ---- ")
    exit(1)

logger.info("DONE")
exit(0)
