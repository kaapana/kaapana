import os
import time
import glob
from datetime import datetime
from pathlib import Path
from shutil import rmtree
from os.path import join, basename, normpath
import logging
from monai.bundle import download

processed_count = 0
max_retries = 3
max_hours_since_creation = 3

workflow_dir = os.getenv('WORKFLOW_DIR', "data")
output_dir = os.getenv('OPERATOR_OUT_DIR', "/models")

target_level = os.getenv('TARGET_LEVEL', "default")

models = os.getenv('MODELS', "NONE") ### "model1:vers1,model2:vers_model2"
models = None if models == "NONE" else models
mode = os.getenv('MODE', "install_pretrained")

logging.info("# Starting GetModelOperator ...")
logging.info("#")
logging.info(f"# mode: {mode}")
logging.info(f"# model: {models}")
logging.info(f"# output_dir: {output_dir}")
logging.info(f"# workflow_dir: {workflow_dir}")
logging.info(f"# target_level: {target_level}")
logging.info("#")
logging.info("#")

def check_dl_running(model_path_dl_running, model_path, wait=True):
    if os.path.isfile(model_path_dl_running):
        hours_since_creation = int((datetime.now() - datetime.fromtimestamp(os.path.getmtime(model_path_dl_running))).total_seconds()/3600)
        if hours_since_creation > max_hours_since_creation:
            logging.info("Download lock-file present! -> waiting until it is finished!")
            logging.info("File older than {} hours! -> removing and triggering download!".format(max_hours_since_creation))
            delete_file(model_path_dl_running)
            return False

        logging.info("Download already running -> waiting until it is finished!")
        while not os.path.isdir(model_path) and wait:
            time.sleep(15)
        return True
    else:
        logging.info("Download not running -> download!")
        return False


def delete_file(target_file):
    try:
        os.remove(target_file)
    except Exception as e:
        logging.info(e)
        pass


logging.info("------------------------------------")
logging.info(f"--     MODE: {mode}")
logging.info("------------------------------------")
if mode == "install_pretrained":
    models_dir = os.path.join(os.getenv("OPERATOR_OUT_DIR", "models"),"monai") ### https://docs.monai.io/en/latest/mb_specification.html
    Path(models_dir).mkdir(parents=True, exist_ok=True)
    
    if models is None:
        logging.info("No ENV 'MODELS' found!")
        logging.info("Abort.")
        exit(1)

    if models == "all":
        logging.info("Downloading all monai-models...")
        models = [
            "spleen_ct_segmentation:0.3.1"
        ]
    else:
        models = models.split(",")
    logging.info("models in the end: {}".format(models))

    for model in models:
        try:
            model_name, version = model.split(":")
        except IndexError as e:
            logging.error("No version specified!")
            raise e
            

        model_path = os.path.join(models_dir, model_name +"_v" + version)
        logging.info("Check if version already present: {}".format(model_path))
        logging.info("MODEL: {}".format(model_name))
        logging.info("VERSION: {}".format(version))

        models_found = glob.glob(join(models_dir,"**",model_name),recursive=True)
        if len(models_found) > 0:
            logging.info("Model {} found!".format(model_name))
            continue

        logging.info("Model not present: {}".format(model_path))

        model_path_dl_running = os.path.join(models_dir, "dl_{}.txt".format(model_name))
        wait = True if len(models) == 1 else False
        if check_dl_running(model_path_dl_running=model_path_dl_running, model_path=model_path, wait=wait):
            continue

        output_dir = os.path.join('/', os.getenv("WORKFLOW_DIR", "tmp"), model_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        try_count = 0
        file_name = f"{model_name}_v{version}.zip"
        target_file = os.path.join(output_dir, file_name)
        while not os.path.isfile(target_file) and try_count < max_retries:
            try_count += 1
            try:
                logging.info("set lock-file: {}".format(model_path_dl_running))
                Path(model_path_dl_running).touch()
                model_version = None if version=="latest" else version
                download(name=model_name, version=model_version, bundle_dir=output_dir)
            except Exception as e:
                logging.info("Could not download model: {}".format(model_name))
                logging.info("Abort.")
                logging.info('MSG: ' + str(e))
                delete_file(target_file)

        if try_count >= max_retries:
            logging.info("------------------------------------")
            logging.info("Max retries reached!")
            logging.info("Skipping...")
            logging.info("------------------------------------")
            delete_file(model_path_dl_running)
            continue

        delete_file(model_path_dl_running)

    logging.info("------------------------------------")
    logging.info("------------------------------------")
    logging.info("Check if all models are now present: {}".format(model_path))
    logging.info("------------------------------------")
    for model in models:
        try:
            model_name, version = model.split(":")
        except IndexError as e:
            logging.error("No version specified!")
            raise e
        model_path = os.path.join(models_dir, model_name, version)
        if os.path.isdir(model_path):
            logging.info("Model {} found!".format(model_name))
            logging.info("------------------------------------")
            continue
        else:
            logging.info("------------------------------------")
            logging.info("------------------------------------")
            logging.info("------------   ERROR!  -------------")
            logging.info("------------------------------------")
            logging.info("Model NOT found: {}".format(model_path))
            logging.info("------------------------------------")
            logging.info("------------------------------------")
            exit(1)

    logging.info("# ✓ All models successfully downloaded and extracted!")

elif mode == "uninstall":
    if models is None:
        logging.info("No ENV 'MODEL' found!")
        logging.info("Abort.")
        exit(1)

    models_dir = "/models/monai"

    logging.info(f"Un-installing TASK: {models}")
    installed_models = [basename(normpath(f.path)) for f in os.scandir(models_dir) if f.is_dir()]

    for installed_model in installed_models:
        model_path = join(models_dir, installed_model)
        installed_tasks_dirs = [basename(normpath(f.path)) for f in os.scandir(model_path) if f.is_dir()]
        for installed_task in installed_tasks_dirs:
            if installed_task.lower() in models.lower():
                task_path = join(models_dir, installed_model, installed_task)
                logging.info(f"Removing: {task_path}")
                rmtree(task_path)
else:
    logging.info("------------------------------------")
    logging.info("------------   ERROR!  -------------")
    logging.info("------------------------------------")
    logging.info(f"---- Mode not supported: {mode} ---- ")
    logging.info("------------------------------------")
    logging.info("------------------------------------")
    exit(1)

logging.info("DONE")
exit(0)
