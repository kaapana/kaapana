from pathlib import Path
from typing import Optional
import numpy as np
import pydicom as pd
import math
from generic import convert_dicom_to_thumbnail
from kaapanapy.logger import get_logger
from PIL import Image

logger = get_logger(__name__)


def generate_histopathology_thumbnail(
    operator_in_dir: Path, thumbnail_size: int
) -> Optional[Image.Image]:
    """
    Generates a thumbnail from a microscopy image.

    This function takes a directory containing DICOM files and generates a thumbnail
    image of the first microscopy image found in the directory. The thumbnail is
    resized to the specified thumbnail size.

    Args:
        operator_in_dir (Path): The directory containing the DICOM files.
        thumbnail_size (int): The size of the thumbnail image.

    Returns:
        Image: The generated thumbnail image.
    """
    dicom_files = list(operator_in_dir.glob("*.dcm"))

    if not dicom_files:
        raise ValueError("No DICOM files found in the directory.")

    LuT = {}
    for file in dicom_files:
        dcm_file = pd.dcmread(file)
        image_type = dcm_file['ImageType'][2]
        if image_type not in LuT:
            LuT[image_type] = [file]
        else:
            LuT[image_type].append(file)

    if 'OVERVIEW' in LuT:
        file = LuT['OVERVIEW'][0]
    elif 'LABEL' in LuT:
        file = LuT['LABEL'][0]
    else:
        NumberOfFrames = np.inf
        dicom_files = []
        # Iterate over the DICOM files to collect their number of frames and Rows
        for i in LuT['VOLUME']:
            dcm_file = pd.dcmread(i)
            FramesOfFile = dcm_file.NumberOfFrames  # int(dcm_file[0x0028, 0x0008].value)
            CubicShape = dcm_file.Rows
            dicom_files.append((i, FramesOfFile, CubicShape))
        # Sort the list of files in descending order by the number of frames
        dicom_files.sort(key=lambda x: x[1], reverse=True)
        threshold_value = 10000000  # Change this value to computational ressources, it fits a 3x3 image with 1024x1024 pixels
        # Find the first file in the last third of the list
        start_index = len(dicom_files) // 3 * 2
        selected_file = None
        for i in range(start_index, len(dicom_files)):
            file, frames, rows = dicom_files[i]
            if rows * rows * frames < threshold_value:
                selected_file = file
                break
        # If no file was found, select the last file with fewer frames
        if not selected_file:
            selected_file = dicom_files[-1][0]

    def create_wsi_thumbnail(file,size):
        dcm_file = pd.dcmread(file)
        if dcm_file['ImageType'][2] == 'OVERVIEW' or dcm_file['ImageType'][2] == 'LABEL':
            image = dcm_file.pixel_array
            image = Image.fromarray(image)
        else:
            if int(dcm_file.NumberOfFrames) == 1:
                image = Image.fromarray(dcm_file.pixel_array)
            else:
                image_array = dcm_file.pixel_array
                TotalPixelMatrixRows = dcm_file.TotalPixelMatrixRows
                TotalPixelMatrixColumns = dcm_file.TotalPixelMatrixColumns
                tiles_per_row = math.ceil(TotalPixelMatrixColumns / image_array.shape[2])  # 3072 / 1024 = 3
                tiles_per_col = math.ceil(TotalPixelMatrixRows / image_array.shape[1])  # 3072 / 1024 = 3

                # Reconstruct the original image
                reconstructed_image = np.zeros(
                    (tiles_per_col * image_array.shape[1], tiles_per_row * image_array.shape[1], 3),
                    dtype=image_array.dtype)
                frame_idx = 0
                for row in range(tiles_per_col):
                    for col in range(tiles_per_row):
                        row_start = row * image_array.shape[1]
                        row_end = row_start + image_array.shape[1]
                        col_start = col * image_array.shape[2]
                        col_end = col_start + image_array.shape[2]
                        reconstructed_image[row_start:row_end, col_start:col_end, :] = image_array[
                            frame_idx]  ###es geht über boundary hinaus
                        frame_idx += 1
                image = reconstructed_image[:TotalPixelMatrixRows, :TotalPixelMatrixColumns, :]
                coords = np.argwhere(image[:, :, 0])
                x_min, y_min = coords.min(axis=0)
                x_max, y_max = coords.max(axis=0)
                b = cropped = image[x_min:x_max + 1, y_min:y_max + 1]
                image = Image.fromarray(b)
        return image.resize(size).convert('RGB')

    thumbnail = create_wsi_thumbnail(file,thumbnail_size)


    return thumbnail
