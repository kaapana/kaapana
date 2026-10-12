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
    relative_dir, _, checkpoint_name = task_ids.partition("/")
    models_root = MODELS_ROOT.resolve()
    source_dir = (models_root / relative_dir).resolve()
    checkpoint = (source_dir / checkpoint_name).resolve()

    # TASK_IDS is part of the run request. A value with ".." must not read files outside the models directory.
    if source_dir.parent != models_root or checkpoint.parent != source_dir:
        raise ValueError(f"Invalid TASK_IDS '{task_ids}'. Expected '<model directory>/<checkpoint file>'.")

    # The model registry can still list a model whose files were deleted.
    # A clear message helps the user to select another model.
    missing = [str(path) for path in (source_dir / "config.json", checkpoint) if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            f"The model '{task_ids}' is not available anymore. Missing files: {', '.join(missing)}. "
            "Select another model."
        )

    OUTPUT_MOUNT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_dir / "config.json", OUTPUT_MOUNT / "config.json")
    shutil.copy2(checkpoint, OUTPUT_MOUNT / checkpoint.name)
    logger.info(f"Copied model '{task_ids}' from {source_dir} to {OUTPUT_MOUNT}")


if __name__ == "__main__":
    task_ids = os.environ["TASK_IDS"]
    if not task_ids:
        raise ValueError("TASK_IDS is empty — select a model via the TASK_IDS workflow parameter.")
    download_model(task_ids)
