import argparse
import ast
import json
import logging
import os

import numpy as np
import SimpleITK as sitk
from skimage.transform import resize

# Create a custom logger
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)

c_format = logging.Formatter("%(levelname)s - %(message)s")
c_handler.setFormatter(c_format)

# Add handlers to the logger
logger.addHandler(c_handler)

# The input and output channels in processing-container.json define these paths.
NRRD_MOUNT = "/kaapana/app/nrrd"
PREPROCESSED_MOUNT = "/kaapana/app/preprocessed"
MODEL_MOUNT = "/kaapana/app/model"


def read_patch_size_from_model() -> str:
    # Inference must resize every image to the patch size that the model was trained with.
    config_path = os.path.join(MODEL_MOUNT, "config.json")
    if not os.path.isfile(config_path):
        raise FileNotFoundError(
            f"{config_path} does not exist. Connect the model input to the output of the model-download task."
        )
    with open(config_path, "r") as file:
        return json.load(file)["PATCH_SIZE"]


class ZScoreNormalizer:
    def normalize(self, image, mask=None):
        return (image - np.mean(image)) / np.std(image)


def compute_statistics(data):
    stats = {}
    stats["dimensions"] = data.shape
    stats["mean"] = float(np.mean(data))
    stats["median"] = float(np.median(data))
    stats["std"] = float(np.std(data))
    stats["min"] = float(np.min(data))
    stats["max"] = float(np.max(data))
    stats["percentile_99_5"] = float(np.percentile(data, 99.5))
    stats["percentile_00_5"] = float(np.percentile(data, 0.5))
    return stats


def resample_image(patient, order=3):
    tuple_from_string = ast.literal_eval(os.environ["PATCH_SIZE"])
    new_shape = np.array(tuple_from_string)
    resized = resize(
        sitk.GetArrayFromImage(patient["image"]).squeeze(),
        new_shape,
        order=order,
        mode="edge",
        anti_aliasing=False,
        preserve_range=True,
    )
    return resized


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--patch-size-from-model",
        action="store_true",
        help="Read the patch size from config.json of the model input instead of PATCH_SIZE.",
    )
    if parser.parse_args().patch_size_from_model:
        os.environ["PATCH_SIZE"] = read_patch_size_from_model()

    batch = {}

    for patient in os.listdir(NRRD_MOUNT):
        # Log
        logger.debug(f"Preprocessing for case {patient} started")

        patient_dict = {}

        patient_dict["image"] = sitk.ReadImage(os.path.join(NRRD_MOUNT, patient, patient + ".nrrd"))

        spacing = patient_dict["image"].GetSpacing()

        if len(spacing) > 3:
            raise ValueError("Not covering the scope of >3-dimensional arrays: E.g. 2 images in one")

        patient_dict["stats"] = compute_statistics(sitk.GetArrayFromImage(patient_dict["image"]))

        # Resample
        data_resampled = resample_image(patient_dict)

        # Normalize
        normalizer = ZScoreNormalizer()
        data_normalized = normalizer.normalize(data_resampled)

        target_dir = os.path.join(PREPROCESSED_MOUNT, patient)
        os.makedirs(target_dir, exist_ok=True)
        np.save(os.path.join(target_dir, patient + ".npy"), data_normalized)

        # Log
        logger.debug(f"{patient} was preprocessed")
