#!/usr/bin/env python3
import ast
import json
import logging
import os
import shutil
from pathlib import Path

import requests
from kaapanapy.settings import ServicesSettings

MODEL_INPUT_MOUNT = "/kaapana/app/model"

logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)
c_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
logger.addHandler(c_handler)


def persist_model(model_dir, models_dir):
    model_path = Path(model_dir)
    config_file = model_path / "config.json"
    if not config_file.exists():
        raise FileNotFoundError(
            f"No config.json found in {model_dir}; the training task did not produce a model output."
        )
    with open(config_file) as f:
        cfg = json.load(f)

    dest_dir = Path(models_dir, f"{cfg['MODEL_CHECKPOINT_NAME']}-fold-{cfg['FOLD']}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    for item in model_path.iterdir():
        shutil.copy2(item, dest_dir / item.name)
    logger.info(f"Persisted model from {model_dir} to {dest_dir}")
    return dest_dir


def _get_installed_classification_models(models_dir):
    installed = {}
    models_path = Path(models_dir)
    if not models_path.exists():
        return installed
    for folder in sorted(models_path.iterdir()):
        if not folder.is_dir():
            continue
        config_file = folder / "config.json"
        if not config_file.exists():
            continue
        best_model = folder / "model-best.pth.tar"
        end_model = folder / "model-end.pth.tar"
        if best_model.exists():
            model_file = best_model.name
        elif end_model.exists():
            model_file = end_model.name
        else:
            logger.warning(f"Skipping {folder.name}: no model checkpoint found (training still running or failed)")
            continue
        with open(config_file) as f:
            cfg = json.load(f)
        model_checkpoint_name = cfg.get("MODEL_CHECKPOINT_NAME", folder.name)
        fold = cfg.get("FOLD", "0")
        tag_map = ast.literal_eval(cfg.get("TAG_TO_CLASS_MAPPING_JSON", "{}"))
        friendly_name = f"classification_{model_checkpoint_name}_fold_{fold}"
        installed[friendly_name] = {
            "description": f"Classification ({cfg.get('TASK', 'N/A')})",
            "task_ids": f"{folder.name}/{model_file}",
            "targets": list(tag_map.keys()),
            "task": cfg.get("TASK", "N/A"),
        }
    return installed


def get_project(identifier: str, aii_root_url: str) -> dict:
    r = requests.get(f"{aii_root_url}/projects/{identifier}")
    r.raise_for_status()
    return r.json()


def sync_models_in_database(models_dir):
    installed = _get_installed_classification_models(models_dir)
    if not installed:
        logger.warning("No classification models found to sync.")
        return
    logger.info(f"Syncing {len(installed)} classification model(s) to database...")
    for name, meta in installed.items():
        logger.info(f"  -> {name}: task_ids={meta['task_ids']}, targets={meta['targets']}")
    project = get_project(
        identifier=os.getenv("KAAPANA_PROJECT_IDENTIFIER"),
        aii_root_url=ServicesSettings().aii_url,
    )
    query_url = f"{ServicesSettings().kaapana_backend_url}/client/installed_models/sync"
    res = requests.put(
        query_url,
        json={"installed_models": installed, "kind": "classification"},
        headers={"Project": json.dumps(project)},
    )
    if res.status_code != 200:
        raise Exception(f"sync_models_in_database failed [{res.status_code}]: {res.text}")
    logger.info(f"Successfully synced {len(installed)} classification model(s) to database.")


if __name__ == "__main__":
    models_dir = f"/models/{os.environ['DAG_ID']}"
    persist_model(MODEL_INPUT_MOUNT, models_dir)
    sync_models_in_database(models_dir=models_dir)
