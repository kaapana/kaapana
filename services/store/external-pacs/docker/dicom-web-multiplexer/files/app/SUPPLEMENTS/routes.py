import io
import numpy as np
import requests

import httpx
import pydicom
from app.auth import get_external_token
from app.logger import get_logger
from app.utils import rs_endpoint_url

from PIL import Image
from fastapi import APIRouter, Request, Response
from fastapi.responses import Response, StreamingResponse

router = APIRouter()
logger = get_logger(__file__)


async def fetch_thumbnail(url: str, headers: dict) -> bytes:
    """
    Fetches the thumbnail image as bytes.

    Args:
        url (str): The URL to fetch the thumbnail from.
        headers (dict): Headers for the request.

    Returns:
        bytes: The thumbnail image as bytes.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.content


async def series_middle_slice(
    rs_endpoint: str, study: str, series: str, token: str
) -> str:
    """
    Fetches the middle instance UID from a series of DICOM instances.

    Args:
        rs_endpoint (str): The DICOMweb endpoint URL.
        study (str): Study UID.
        series (str): Series UID.
        token (str): Bearer token for authorization.

    Returns:
        str: The SOP Instance UID of the middle instance.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/dicom+json",
    }

    url = f"{rs_endpoint}/studies/{study}/series/{series}/instances"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        instances = response.json()

        # Sorting to find the middle instance
        instance = sorted(
            instances, key=lambda x: x.get("00200013", {"Value": [0]})["Value"][0]
        )[len(instances) // 2]
        object_uid = instance["00080018"]["Value"][0]
        return object_uid


@router.get("/studies/{study}/series/{series}/thumbnail")
async def retrieve_series_thumbnail(
    study: str,
    series: str,
    request: Request,
):
    """
    Endpoint to retrieve a thumbnail of a specific series.

    Args:
        study (str): Study UID.
        series (str): Series UID.
        request (Request): FastAPI request object containing context information.

    Returns:
        Response: A response containing the thumbnail image, or an error response if retrieval fails.
    """
    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)

    try:
        # Fetch the middle instance UID
        instance = await series_middle_slice(rs_endpoint, study, series, token)
        if not instance:
            return Response(
                status_code=500,
                content="Couldn't find middle slice. Aborting downloading thumbnail ... ",
            )

        # Fetch the thumbnail
        url = f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}/rendered"
        headers = {"Authorization": f"Bearer {token}", "Accept": "image/png"}
        thumbnail_bytes = await fetch_thumbnail(url, headers)

        # Return the thumbnail as a response
        return Response(content=thumbnail_bytes, media_type="image/png")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e}")
        if e.response.status_code == 406:
            logger.error("Unsupported media type (406 Not Acceptable)")
            instance_url = (
                f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}"
            )
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/dicom; transfer-syntax=*",
            }
            response = requests.get(instance_url, headers=headers)
            response.raise_for_status()
            dicom_stream = io.BytesIO(response.content)
            png_image_stream = dicom_to_png(dicom_stream)

            # Return the PNG image as a streaming response
            return StreamingResponse(png_image_stream, media_type="image/png")

        return Response(
            status_code=e.response.status_code,
            content=f"HTTP error occurred: {e}",
        )
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return Response(
            status_code=500,
            content=f"An error occurred while processing the request: {e}",
        )


def dicom_to_png(dicom_stream, frame_number=0):
    """Converts a DICOM image (single instance or specific frame) to PNG."""
    ds = pydicom.dcmread(dicom_stream)

    # Extract pixel data
    if hasattr(ds, "NumberOfFrames") and ds.NumberOfFrames > 1:
        pixel_array = ds.pixel_array[frame_number]  # Extract the specific frame
    else:
        pixel_array = ds.pixel_array

    # Normalize pixel values to 8-bit (0-255)
    pixel_array = pixel_array.astype(np.float32)
    pixel_array -= pixel_array.min()
    pixel_array /= pixel_array.max()
    pixel_array *= 255.0
    pixel_array = pixel_array.astype(np.uint8)

    # Convert to grayscale image
    image = Image.fromarray(pixel_array)

    # Save the image into a BytesIO object (in-memory)
    png_output = io.BytesIO()
    image.save(png_output, format="PNG")
    png_output.seek(0)  # Rewind to the start of the BytesIO stream

    return png_output
