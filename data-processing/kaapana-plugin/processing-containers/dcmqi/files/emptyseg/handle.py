import os
import re
import json
import numpy as np
import nibabel as nib


def get_all_files_from_dir(
    target: str, filter_pattern: str = "", full_path: bool = True
):
    """
    Retrieve a list of files from the specified directory, optionally filtered by a regular expression pattern.

    Parameters:
    - target (str): The path to the target directory.
    - filter_pattern (str, optional): A regular expression pattern to filter filenames. Default is None.
    - full_path (bool, optional): If True, return the full path of each file. Default is True.

    Returns:
    - List[str]: A list of file paths.
    """
    all_files = os.listdir(target)
    if filter_pattern != "":
        all_files = [f for f in all_files if re.match(filter_pattern, f)]

    if full_path:
        all_files = [os.path.join(target, f) for f in all_files]

    return all_files


def get_filename_stem(target: str):
    """
    Extract the filename stem (without extension) from the given file path.

    Parameters:
    - target (str): The file path from which to extract the filename stem.

    Returns:
    - str: The filename stem.
    """
    filename = os.path.basename(target)
    file_splits = filename.split(".")
    return file_splits[0]


def np_from_nifti(nifti_file: str, astype: str = "int"):
    """
    Load a NIfTI file and return its data as a NumPy array.

    Parameters:
    - nifti_file (str): The path to the NIfTI file.
    - astype (str, optional): The desired data type for the NumPy array ('int' or 'float'). Default is 'int'.

    Returns:
    - np.ndarray: The NumPy array containing the NIfTI data.
    """
    nptype = int
    if astype == "float":
        nptype = float

    nifti = nib.load(nifti_file)
    return nifti.get_fdata().astype(nptype)


def np_binarize(np_val, inverse: bool = False):
    """
    Binarize a NumPy array, setting values greater than 0 to 1 and others to 0.

    Parameters:
    - np_val: The input NumPy array.
    - inverse (bool, optional): If True, invert the binarization (1 becomes 0, 0 becomes 1). Default is False.

    Returns:
    - np.ndarray: The binarized NumPy array.
    """
    if inverse:
        return np.where(np_val > 0, 0, 1)
    return np.where(np_val > 0, 1, 0)


def _extract_nifti_files(input_files_dir: str, raise_err: bool = False):
    """
    Extracts / Look for all the NIfTI files from the specified input directory, separating the background base
    NIfTI file or emtpy nifti file named `empty.nii(.gz)` from other nifti files.

    Parameters:
    - input_files_dir (str): The path to the input directory containing NIfTI files.

    Returns:
    - Tuple[str, List[str]]: A tuple containing the path to the background base NIfTI file
    and a list of paths to the remaining NIfTI files in the input directory.
    """
    # Ensure that the provided input directory exists
    if not os.path.isdir(input_files_dir):
        raise FileNotFoundError(
            "Directory not found!! {} is not a valid Minio files input directory.".format(
                input_files_dir
            )
        )

    # Retrieve all files in the input directory matching the NIfTI file format
    all_nifties = get_all_files_from_dir(input_files_dir, filter_pattern=r".*\.nii.*")

    # Initialize a variable to store the background base NIfTI file name
    empty_nifti = None
    seg_labels = []

    # Iterate through each NIfTI file in the list
    for n in all_nifties:
        np_arr = np_from_nifti(n)
        mask_labels = list(np.unique(np_arr))
        seg_labels.extend(mask_labels)

        # find the empty / background nifty by checking if the only label on that nifti is 0
        if len(mask_labels) == 1 and mask_labels[0] == 0:
            # If a match is found, assign the NIfTI file to the background base variable
            empty_nifti = n
            all_nifties.remove(n)
            break

    # If no empty Segmentation NIfTI file is found, raise an exception
    if not empty_nifti and raise_err:
        raise FileNotFoundError(
            "No empty segmentation NIfTI file were not found in the directory {}".format(
                input_files_dir
            )
        )

    # Return the background base NIfTI file and the list of remaining NIfTI files
    return empty_nifti, all_nifties, list(set(seg_labels))


def _create_empty_mask_n_assign_label(
    empty_base_mask: str, other_masks: list, empty_mask_label: int
):
    """
    Creates a background mask by combining a base background mask with additional segmentation masks.

    Parameters:
    - empty_base_mask (str): Path to the base background mask NIfTI file.
    - other_masks (list): List of paths to segmentation masks in NIfTI format.

    Returns:
    - Tuple[nib.Nifti1Image, List[Dict[str, Union[str, int]]]]: A tuple containing the generated background mask
    as a NIfTI image and a list of dictionaries providing information about each segmented region in the mask.
    """
    # Load the base background mask NIfTI file and convert it to a NumPy array
    empty_base_nifti = nib.load(empty_base_mask)
    empty_base_np = np_from_nifti(empty_base_mask)

    # Initialize variables to store segmentation information and the combined segmentation mask
    # seg_info = []
    segmentation_base = np.zeros(empty_base_np.shape, empty_base_np.dtype)

    # Iterate through each segmentation mask file
    for mask_file in other_masks:
        # Load the segmentation mask NIfTI file and extract necessary information
        mask_np = np_from_nifti(mask_file)
        filename = get_filename_stem(mask_file)

        # Extract unique labels from the segmentation mask
        unique_mask_labels = list(np.unique(mask_np))
        if 0 in unique_mask_labels:
            unique_mask_labels.remove(0)

        # Binarize the segmentation mask and add it to the combined segmentation mask
        mask_np = np_binarize(mask_np)
        segmentation_base = np.add(segmentation_base, mask_np)

        # Check for errors in segmentation, such as more than one label
        if len(unique_mask_labels) > 1:
            raise ValueError(
                "Error: More than 1 label in segmentation found in the file {}.".format(
                    os.path.basename(mask_file)
                )
            )

    # Invert the combined segmentation mask and add it to the base background mask
    segmentation_inversed = np_binarize(segmentation_base, inverse=True)
    empty_mask = np.add(empty_base_np, segmentation_inversed)

    # Replace pixels with a value of 1 with the specified background label, and set other pixels to 0
    empty_mask = np.where(empty_mask == 1, empty_mask_label, 0)

    # Create a new NIfTI image from the generated background mask with the same affine and header as the base background mask
    empty_mask_nifti = nib.Nifti1Image(
        empty_mask, empty_base_nifti.affine, empty_base_nifti.header
    )

    # Return the generated background mask and segmentation information
    return empty_mask_nifti


def check_n_replace_empty_mask(input_dir: str, empty_mask_label: int):
    empty_nifti, other_nifties, segmentation_labels = _extract_nifti_files(input_dir)
    if empty_nifti:
        empty_masked_output_nifti_file = _create_empty_mask_n_assign_label(
            empty_nifti, other_nifties, empty_mask_label
        )
        nib.save(empty_masked_output_nifti_file, empty_nifti)

        print("################################")
        print("empty nifti file updated with new empty segmentation mask labels")
        print("################################")

        seg_info_files = get_all_files_from_dir(
            target=input_dir, filter_pattern=r".*seg(-|_)info.json\b"
        )
        if len(seg_info_files) == 0:
            # raise FileNotFoundError(
            #     "No segmentation info file were not found in the directory {}".format(
            #         input_dir
            #     )
            # )
            seg_info_file = os.path.join(input_dir, "seg_info.json")
            seg_info_json = {}
            seg_info_json["seg_info"] = [
                {"label_int": str(empty_mask_label), "label_name": "empty mask"},
            ]

        else:
            seg_info_file = seg_info_files[0]
            with open(seg_info_file) as f:
                seg_info_json = json.load(f)

            updated_seg_info = []

            for seg in seg_info_json["seg_info"]:
                label_id = int(seg["label_int"])
                if label_id == 0:
                    seg["label_int"] = str(empty_mask_label)
                elif label_id not in segmentation_labels:
                    continue

                updated_seg_info.append(seg)

            seg_info_json["seg_info"] = updated_seg_info

        with open(seg_info_file, "w+", encoding="utf8") as json_file:
            json.dump(seg_info_json, json_file, indent=4)

        print("################################")
        print("seg_info.json file updated with new empty segmentation mask labels")
        print("################################")
