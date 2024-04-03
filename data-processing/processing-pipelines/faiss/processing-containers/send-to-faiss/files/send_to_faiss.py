import logging
import os
from pathlib import Path
import pydicom
import requests
from PIL import Image
import io


SERVICES_NAMESPACE = os.environ["SERVICES_NAMESPACE"]

# Create a custom logger
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


def dicom_to_image_bytes(dicom_path):
    """Convert DICOM file to a format suitable for sending in a HTTP request."""
    ds = pydicom.dcmread(dicom_path)
    img = ds.pixel_array
    img = Image.fromarray(img).convert("RGB")  # Convert to RGB
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes = img_bytes.getvalue()
    return img_bytes


def upload_image_to_fastapi(seriesInstanceUID, sopInstanceUID, image_bytes, url):
    """Send an image along with its metadata to the FastAPI application."""
    files = {
        "image": ("image.png", io.BytesIO(image_bytes), "image/png"),
    }
    params = {
        "seriesInstanceUID": seriesInstanceUID,
        "sopInstanceUID": sopInstanceUID,
    }
    logger.info(f"Uploading image for {seriesInstanceUID} - {sopInstanceUID}")
    response = requests.put(url, params=params, files=files)
    return response.json()


if __name__ == "__main__":
    batch_folder = list(Path(os.environ["BATCHES_INPUT_DIR"]).glob("*"))

    for batch_element_dir in batch_folder:
        files = [
            p
            for p in Path(batch_element_dir, os.environ["OPERATOR_IN_DIR"]).rglob("*")
            if pydicom.misc.is_dicom(p)
        ]

        for _file in files:
            try:
                logger.info(f"Send to Faiss: {_file}")
                ds = pydicom.dcmread(_file)
                seriesInstanceUID = ds.SeriesInstanceUID
                sopInstanceUID = ds.SOPInstanceUID
                image_bytes = dicom_to_image_bytes(_file)
                response = upload_image_to_fastapi(
                    seriesInstanceUID,
                    sopInstanceUID,
                    image_bytes,
                    f"http://faiss-chart.{SERVICES_NAMESPACE}.svc:5000/encode",
                )
                logger.info(response)
                logger.info(f"Response for {_file}: {response}")

                # if response.status_code != 200:
                #     logger.error(f"Failed to send {_file} to Faiss.")
                #     exit(1)

            except Exception as e:
                logger.error(f"Processing of {_file} threw an error.", e)
                exit(1)
