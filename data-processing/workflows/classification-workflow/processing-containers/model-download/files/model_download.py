#!/usr/bin/env python3
import logging
import os
import shutil
from pathlib import Path

MODELS_ROOT = Path("/models/classification-training")
OUTPUT_MOUNT = Path("/kaapana/app/model")

logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)
c_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
logger.addHandler(c_handler)


def download_model(task_ids: str) -> None:
    relative_dir, checkpoint_name = task_ids.split("/", 1)
    source_dir = MODELS_ROOT / relative_dir

    OUTPUT_MOUNT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_dir / "config.json", OUTPUT_MOUNT / "config.json")
    shutil.copy2(source_dir / checkpoint_name, OUTPUT_MOUNT / checkpoint_name)
    logger.info(f"Copied model '{task_ids}' from {source_dir} to {OUTPUT_MOUNT}")


if __name__ == "__main__":
    task_ids = os.environ["TASK_IDS"]
    if not task_ids:
        raise ValueError(
            "TASK_IDS is empty — select a model via the TASK_IDS workflow parameter."
        )
    download_model(task_ids)
