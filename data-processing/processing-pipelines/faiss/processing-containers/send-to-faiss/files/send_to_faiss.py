from time import sleep
import os
from pathlib import Path
import pydicom
from PIL import Image
from open_clip import create_model_from_pretrained, get_tokenizer
import torch
import numpy as np

from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from kaapanapy.helper.HelperOpensearch import HelperOpensearch
from kaapanapy.helper import load_workflow_config
from kaapanapy.logger import get_logger
from kaapanapy.settings import OperatorSettings
from pydantic_settings import BaseSettings

import torch
import os

logger = get_logger(__name__)


def dicom_to_image_bytes(dicom_path):
    """Convert DICOM file to a format suitable for sending in a HTTP request."""
    ds = pydicom.dcmread(dicom_path)
    img = ds.pixel_array
    img = Image.fromarray(img).convert("RGB")  # Convert to RGB
    return img


class GetInputArguments(BaseSettings):
    DIMENSION: int = 512
    MODEL_NAME: str = "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"
    DEVICE: str = "cpu"


class Img2Vec2MetaOperator:
    def __init__(self):
        self.max_retries = 10
        self.workflow_config = load_workflow_config()
        self.dcmweb_helper = HelperDcmWeb()
        self.os_helper = HelperOpensearch()
        self.project_form = self.workflow_config.get("project_form")
        self.project_index = self.project_form.get("opensearch_index")
        self.operator_settings = OperatorSettings()
        self.operator_arguments = GetInputArguments()
        logger.debug(f"{self.operator_arguments=}")
        logger.debug(f"{self.workflow_config=}")

        self.model, self.processor = create_model_from_pretrained(
            self.operator_arguments.MODEL_NAME, cache_dir="/models"
        )
        self.model.to(self.operator_arguments.DEVICE).eval()
        self.tokenizer = get_tokenizer(self.operator_arguments.MODEL_NAME)

    def encode_image(
        self,
        image: Image,
    ):
        image = self.processor(image).unsqueeze(0).to(self.operator_arguments.DEVICE)

        with torch.no_grad():
            image_features = self.model.encode_image(image).cpu().numpy()

        # Normalize the feature vector
        image_features = image_features / np.linalg.norm(
            image_features, axis=1, keepdims=True
        )

        return image_features[0]

    def storeInMeta(
        self,
        os_client,
        series_instance_uid: str,
        sop_instance_uid: str,
        image_features: np.ndarray,
    ):
        doc = self.os_helper.os_client.get(
            index=self.project_index, id=series_instance_uid
        )

        body = {
            "script": {
                "source": """
                    if (ctx._source.instances == null) {
                        ctx._source.instances = [];
                    }
                    ctx._source.instances.add(params.new_instance);
                """,
                "lang": "painless",
                "params": {
                    "new_instance": {
                        "sopInstanceUID": f"{sop_instance_uid}",
                        "image_embedding": image_features.tolist(),
                    }
                },
            }
        }

        # Write Tags back
        return os_client.update(
            index=self.project_index, id=series_instance_uid, body=body
        )

    def start(self):
        batch_folder = list(Path(os.environ["BATCHES_INPUT_DIR"]).glob("*"))

        for b_i, batch_element_dir in enumerate(batch_folder):
            files = [
                p
                for p in Path(batch_element_dir, os.environ["OPERATOR_IN_DIR"]).rglob(
                    "*"
                )
                if pydicom.misc.is_dicom(p)
            ]

            for i, _file in enumerate(files):
                retry = 0
                while retry < self.max_retries:
                    try:
                        ds = pydicom.dcmread(_file)
                        seriesInstanceUID = ds.SeriesInstanceUID
                        sopInstanceUID = ds.SOPInstanceUID
                        image = dicom_to_image_bytes(_file)

                        image_features = self.encode_image(image)
                        response = self.storeInMeta(
                            self.os_helper.os_client,
                            seriesInstanceUID,
                            sopInstanceUID,
                            image_features,
                        )
                        # Success: break out of retry loop
                        break

                    except Exception as e:
                        retry += 1
                        logger.info(
                            f"Processing threw an error on attempt {retry}/{self.max_retries} for {_file}: {e}"
                        )
                        if retry >= self.max_retries:
                            logger.error(
                                f"Failed processing {_file} after {self.max_retries} retries. Aborting."
                            )
                            exit(1)
                        # sleep for 1 sec
                        sleep(1)
                logger.info(
                    f"{f'Batch {b_i+1}/{len(batch_folder)}: ' if len(batch_folder) > 1 else ''} ({i+1}/{len(files)}) Successfully processed {_file}"
                )


if __name__ == "__main__":
    operator = Img2Vec2MetaOperator()
    operator.start()
