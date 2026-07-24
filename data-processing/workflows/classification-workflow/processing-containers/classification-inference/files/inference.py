#!/usr/bin/env python3
import ast
import json
import logging
import os

import numpy as np
import torch
from batchgenerators.dataloading.multi_threaded_augmenter import MultiThreadedAugmenter
from batchgenerators.transforms.abstract_transforms import Compose
from batchgenerators.transforms.sample_normalization_transforms import (
    ZeroMeanUnitVarianceTransform,
)
from batchgenerators_dataloader import PREPROCESSED_MOUNT, ClassificationDataset
from monai.networks.nets import resnet18
from opensearch_helper import OpenSearchHelper

# Fixed mount path, defined by this container's processing-container.json
# ("infer" template: "model" input channel, provided by the model-download task).
MODEL_MOUNT = "/kaapana/app/model"

# Create a custom logger
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)

c_format = logging.Formatter("%(levelname)s - %(message)s")
c_handler.setFormatter(c_format)

# Add handler to the logger
logger.addHandler(c_handler)

# load config

with open(os.path.join(MODEL_MOUNT, "config.json"), "r") as file:
    # Load the JSON content from the file
    CONFIG = json.load(file)

TAG_TO_CLASS_MAPPING = ast.literal_eval(CONFIG["TAG_TO_CLASS_MAPPING_JSON"])
CLASS_TO_TAG_MAPPING = {v: k for k, v in TAG_TO_CLASS_MAPPING.items()}
NUM_CLASSES = 1 if CONFIG["TASK"] == "binary" else len(TAG_TO_CLASS_MAPPING)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
NUM_INPUT_CHANNELS = 1
PATCH_SIZE = np.array(ast.literal_eval(CONFIG["PATCH_SIZE"]))
NUM_WORKERS = 4
BATCH_SIZE = int(CONFIG["BATCH_SIZE"])
os.environ["TASK"] = CONFIG["TASK"]
TAG_POSTFIX = os.environ["TAG_POSTFIX"].lower() == "true"
MODEL_CHECKPOINT_NAME = CONFIG["MODEL_CHECKPOINT_NAME"]
FOLD = CONFIG["FOLD"]

# Log config

logger.debug(f"TAG_TO_CLASS_MAPPING_JSON={CONFIG['TAG_TO_CLASS_MAPPING_JSON']}")
logger.debug(f"TASK={CONFIG['TASK']}")
logger.debug(f"NUM_EPOCHS={CONFIG['NUM_EPOCHS']}")
logger.debug(f"DIMENSIONS={CONFIG['DIMENSIONS']}")
logger.debug(f"PATCH_SIZE={CONFIG['PATCH_SIZE']}")
logger.debug(f"BATCH_SIZE={CONFIG['BATCH_SIZE']}")
logger.debug(f"TASK={CONFIG['TASK']}")
logger.debug(f"MODEL_CHECKPOINT_NAME of training={CONFIG['MODEL_CHECKPOINT_NAME']}")
logger.debug(f"FOLD={CONFIG['FOLD']}")


def inference(model, mt_val):
    model.eval()
    final_predictions = {}

    for _, batch in enumerate(mt_val):
        x = torch.from_numpy(batch["data"]).to(DEVICE)
        samples = batch["samples"]
        with torch.no_grad():
            outputs = model(x)

            predictions = torch.round(torch.sigmoid(outputs)).detach().cpu().numpy()

            for i in range(len(predictions)):
                final_predictions[samples[i]] = CLASS_TO_TAG_MAPPING[
                    int(predictions[i][0])
                ]

    return final_predictions


if __name__ == "__main__":
    spatial_dims = int(CONFIG["DIMENSIONS"][0])

    model = resnet18(
        pretrained=False,
        progress=True,
        spatial_dims=spatial_dims,
        n_input_channels=NUM_INPUT_CHANNELS,
        num_classes=NUM_CLASSES,
    )

    checkpoint_candidates = [
        f for f in os.listdir(MODEL_MOUNT) if f.endswith(".pth.tar")
    ]
    if len(checkpoint_candidates) != 1:
        raise FileNotFoundError(
            f"Expected exactly one checkpoint file in {MODEL_MOUNT}, found {checkpoint_candidates}"
        )
    checkpoint_filename = checkpoint_candidates[0]
    path_to_checkpoint_file = os.path.join(MODEL_MOUNT, checkpoint_filename)

    # load weights
    # using weights_only=False for backwards compatability to keep torch <2.6 behavior
    # TODO: get rid of it via
    # Option 1 : updating the model saving to ensure all checkpoint objects are native Python types instead of NumPy types before torch.save()
    # Option 2: using safe_globals to whitelist the specific numpy scalar type found in legacy checkpoints
    checkpoint = torch.load(path_to_checkpoint_file, map_location=DEVICE, weights_only=False)
    model.load_state_dict(checkpoint["state_dict"], strict=False)

    # load on gpu

    model = model.to(DEVICE)

    logger.debug("Load model on gpu")

    model.eval()

    all_samples = os.listdir(PREPROCESSED_MOUNT)

    dl_val = ClassificationDataset(
        data=all_samples,
        batch_size=BATCH_SIZE,
        patch_size=PATCH_SIZE,
        num_threads_in_multithreaded=NUM_WORKERS,
        return_incomplete=False,
        shuffle=False,
        num_modalities=NUM_INPUT_CHANNELS,
        num_classes=NUM_CLASSES,
    )

    mt_val = MultiThreadedAugmenter(
        data_loader=dl_val,
        transform=Compose([ZeroMeanUnitVarianceTransform()]),
        num_processes=NUM_WORKERS,
        num_cached_per_queue=4,
        pin_memory=True,
    )

    # Inference loop

    logger.debug("Inference loop")

    mt_val._start()

    predictions = inference(model, mt_val)

    mt_val._finish()

    # Add the tags to opensearch

    for id, tag in predictions.items():
        tag = (
            f"{tag}-{MODEL_CHECKPOINT_NAME}-{FOLD}-{'end' if 'end' in checkpoint_filename else 'best'}"
            if TAG_POSTFIX
            else tag
        )
        OpenSearchHelper.add_tag_to_id(id, tag)
