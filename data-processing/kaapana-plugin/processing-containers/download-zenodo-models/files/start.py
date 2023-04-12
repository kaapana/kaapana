import os
import urllib.request
import zipfile
import time
from datetime import datetime
from pathlib import Path
from shutil import rmtree
from alive_progress import alive_bar
from os.path import join, basename, normpath, isfile, getmtime, exists, dirname
from os import getenv
import json
import pathlib
import logging

from logger_helper import get_logger

success_count = 0
processed_count = 0
max_retries = 3
waiting_timeout_sec = 7200
max_hours_since_creation = 3
model_dir = getenv("MODEL_DIR", "None")
model_dir = model_dir if model_dir.lower() != "none" else None
assert model_dir is not None

task_ids = getenv("TASK_IDS", "None")
task_ids = None if task_ids == "None" else task_ids
task_ids = task_ids.split(",")

log_level = getenv("LOG_LEVEL", "info").lower()
log_level_int = None
if log_level == "debug":
    log_level_int = logging.DEBUG
elif log_level == "info":
    log_level_int = logging.INFO
elif log_level == "warning":
    log_level_int = logging.WARNING
elif log_level == "critical":
    log_level_int = logging.CRITICAL
elif log_level == "error":
    log_level_int = logging.ERROR

logger = get_logger(__name__, log_level_int)
pbar = None
pbar_count = 0


def bar_update(block_num, block_size, total_size):
    global pbar, pbar_count

    downloaded = block_num * block_size
    one_percent = total_size // 100
    percent_done = downloaded // one_percent

    for i in range(0, percent_done - pbar_count):
        pbar()
        pbar.text(f"{downloaded} / {total_size}")

    if percent_done != pbar_count:
        logger.info(f"{percent_done} / 100 % Done")
        pbar_count = percent_done


def check_dl_running(model_download_lockfile_path, model_path, wait=True):
    if isfile(model_download_lockfile_path):
        hours_since_creation = int(
            (
                datetime.now()
                - datetime.fromtimestamp(getmtime(model_download_lockfile_path))
            ).total_seconds()
            / 3600
        )
        if hours_since_creation > max_hours_since_creation:
            logger.warning(
                "Download lock-file present! -> waiting until it is finished!"
            )
            logger.warning(
                f"File older than {max_hours_since_creation} hours! -> removing and triggering download!"
            )
            delete_file(model_download_lockfile_path)
            return False

        logger.warning("Download already running -> waiting until it is finished!")
        start_time = time.time()
        while (
            not os.path.isdir(model_path)
            and (time.time() - start_time) <= waiting_timeout_sec
            and wait
        ):
            time.sleep(15)
        if (time.time() - start_time) > waiting_timeout_sec:
            logger.warning("Waiting for download timeout of 2h reached! -> abort.")
            delete_file(model_download_lockfile_path)
            return False
        else:
            return True
    else:
        logger.info("# Download not running -> download!")
        return False


def unzip_model(model_zip_file, target_dir):
    global max_retries

    assert exists(model_zip_file)

    try:
        with zipfile.ZipFile(model_zip_file, "r") as zip_ref:
            zip_ref.extractall(target_dir)

    except Exception as e:
        logger.error(f"Could not extract model: {model_zip_file}")
        logger.error(f"Target dir: {target_dir}")
        logger.error("MSG: " + str(e))


def download_model(model_download_zip_tmp_path, model_url):
    global max_retries, pbar

    try_count = 0
    while not isfile(model_download_zip_tmp_path) and try_count < max_retries:
        logger.info(f"Try: {try_count} - Start download: {model_url}")
        try_count += 1
        try:
            logger.info(f"set lock-file: {model_download_lockfile_path}")
            Path(model_download_lockfile_path).touch()
            with alive_bar(
                100,
                dual_line=True,
                title=f"Downloading {model_download_zip_tmp_path}",
            ) as bar:
                pbar = bar
                urllib.request.urlretrieve(
                    model_url, model_download_zip_tmp_path, bar_update
                )
        except Exception as e:
            logger.error(f"Could not download model: {model_url} -> exit.")
            logger.error("MSG: " + str(e))
            delete_file(model_download_zip_tmp_path)
            delete_file(model_download_lockfile_path)

    if isfile(model_download_zip_tmp_path):
        return True
    else:
        return False


def delete_file(target_file):
    try:
        os.remove(target_file)
    except Exception as e:
        logger.info(e)
        pass


if __name__ == "__main__":
    logger.info("# Starting GetModelOperator ...")
    logger.info("#")
    logger.info(f"# {model_dir=}")
    logger.info(f"# {task_ids=}")
    logger.info("#")
    logger.info("#")

    issues_occurred = False
    json_path = join(pathlib.Path(__file__).parent.resolve(), "model_lookup.json")

    with open(json_path, encoding="utf-8") as model_lookup:
        model_lookup_dict = json.load(model_lookup)

    if task_ids[0] == "all":
        task_ids = list(model_lookup_dict.keys())

    for rounds in range(0, 2):
        logger.info(f"####### round: {rounds}")
        success_count = 0
        for task_id in task_ids:
            tmp_success = False
            assert task_id in model_lookup_dict
            task_url = model_lookup_dict[task_id]["download_link"]
            task_models = model_lookup_dict[task_id]["models"]
            check_file = model_lookup_dict[task_id]["check_file"]
            for task_model in task_models:
                model_target_dir = join(model_dir, task_model, task_id)

                if check_file == "default":
                    check_file_path=join(model_target_dir,"nnUNetTrainerV2__nnUNetPlansv2.1","plans.pkl")
                else:
                    check_file_path=join(model_target_dir,check_file)

                logger.info(f"Check if model already present: {check_file_path}")
                if exists(check_file_path):
                    logger.info(f"{task_id} already exisis @{check_file_path} -> skipping")
                    success_count += 1
                    continue

                model_download_zip_tmp_path = join(
                    model_dir, "tmp-download", f"{task_id}.zip"
                )
                model_download_lockfile_path = join(
                    model_dir, "tmp-download", f"{task_id}.lock"
                )
                os.makedirs(dirname(model_download_zip_tmp_path), exist_ok=True)

                logger.info(f"{task_id} check if already running ...")
                already_completed = check_dl_running(
                    model_download_lockfile_path=model_download_lockfile_path,
                    model_path=model_target_dir,
                    wait=True,
                )

                if not already_completed:
                    logger.info(f"{task_id} start download ...")
                    download_success = download_model(
                        model_url=task_url,
                        model_download_zip_tmp_path=model_download_zip_tmp_path,
                    )
                else:
                    download_success = True

                if not download_success:
                    issues_occurred = True
                    logger.error(f"{task_id} download was not successful! ")
                    continue

                logger.info(f"{task_id} start unzipping ...")
                unzip_model(
                    model_zip_file=model_download_zip_tmp_path,
                    target_dir=model_dir
                    if "total_segmentator" not in model_dir
                    else join(model_dir, task_model),
                )
                delete_file(model_download_zip_tmp_path)
                delete_file(model_download_lockfile_path)

                logger.info(f"{task_id} checking result @{check_file_path} ...")
                if not exists(check_file_path):
                    rmtree(model_target_dir)
                    logger.error(f"{task_id} model resulting could not be found! ")
                    issues_occurred = True
                    continue
                else:
                    logger.info(f"{task_id}: {task_model} ✓ everything is fine -> DONE")
                    tmp_success = True

            if tmp_success:
                success_count += 1

    if issues_occurred and success_count != len(task_ids):
        logger.info("# Something went wrong ...")
        print(f"success_count: {success_count} != len(task_ids): {len(task_ids)}")
        exit(1)

    logger.info("# ✓ successfully extracted model into model-dir.")
    logger.info("# DONE")
    exit(0)
