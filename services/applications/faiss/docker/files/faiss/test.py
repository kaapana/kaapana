from pathlib import Path
import pydicom
from PIL import Image
import io
import aiohttp
import asyncio


async def dicom_to_image_bytes(dicom_path):
    """Convert DICOM file to a format suitable for sending in a HTTP request."""
    ds = pydicom.dcmread(dicom_path)
    # Assuming the DICOM image is grayscale
    img = ds.pixel_array
    img = Image.fromarray(img).convert("RGB")  # Convert to RGB
    # Convert image to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes = img_bytes.getvalue()
    return img_bytes


async def upload_image_to_fastapi(
    seriesInstanceUID, sopInstanceUID, image_bytes, url="http://localhost:5000/encode"
):
    """Send an image along with its metadata to the FastAPI application."""
    image_stream = io.BytesIO(image_bytes)
    image_stream.name = "image.png"

    # Constructing the multipart/form-data request
    data = aiohttp.FormData()
    data.add_field(
        "image", image_stream, filename="image.png", content_type="image/png"
    )

    # Prepare query parameters
    params = {"seriesInstanceUID": seriesInstanceUID, "sopInstanceUID": sopInstanceUID}

    print(f"Uploading image for {seriesInstanceUID} - {sopInstanceUID}")
    # Make the asynchronous PUT request with query parameters
    async with aiohttp.ClientSession() as session:
        async with session.put(url, params=params, data=data) as response:
            return await response.json()


async def process_file(filepath):
    """Process a single DICOM file."""
    try:
        ds = pydicom.dcmread(filepath)
        seriesInstanceUID = ds.SeriesInstanceUID
        sopInstanceUID = ds.SOPInstanceUID
        image_bytes = await dicom_to_image_bytes(filepath)
        response = await upload_image_to_fastapi(
            seriesInstanceUID, sopInstanceUID, image_bytes
        )
        print(f"Response for {filepath.name}: {response}")
    except Exception as e:
        print(f"Error processing {filepath.name}: {e}")


async def main(directory_path):
    """Process all DICOM files in the specified directory asynchronously."""
    tasks = [process_file(filepath) for filepath in directory_path.rglob("*.dcm")]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    directory_path = Path(
        "/home/s037r/Documents/DATASETS/TCIA_LIDC-IDRI_20200921/LIDC-IDRI/LIDC-IDRI-0002"
    )
    asyncio.run(main(directory_path))
