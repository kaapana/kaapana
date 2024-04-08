import os
import shutil
import glob
import nibabel as nib
import numpy as np
import dicom2nifti


from .handle import get_all_files_from_dir, np_from_nifti


def get_shape_from_nifties(nifti_path: str):
    # Retrieve all files in the input directory matching the NIfTI file format
    all_nifties = get_all_files_from_dir(nifti_path, filter_pattern=r".*\.nii.*")

    if len(all_nifties) == 0:
        raise FileNotFoundError(
            "No nifti file found in the directory {} to be used as a base nifti for empty segmentation file.".format(
                nifti_path
            )
            + "Provide base_nifti_dir parameter to avoid such errors"
        )

    base_nifti = nib.load(all_nifties[0])
    base_nifti_np = np_from_nifti(all_nifties[0])

    return base_nifti_np.shape, base_nifti_np.dtype, base_nifti


def get_shape_from_dicoms(dicom_path: str):
    dicom_files = get_all_files_from_dir(dicom_path, filter_pattern=r".*\.dcm")

    if len(dicom_files) == 0:
        raise FileNotFoundError(
            "No dicom file found in the directory {} to be used as a base dicom for empty segmentation file.".format(
                dicom_path
            )
            + "Provide valid dicom input directory to avoid such errors"
        )

    temp_nifti_dir = os.path.join(os.path.dirname(dicom_path), "temp_dicoms_2312")
    os.mkdir(temp_nifti_dir)

    dicom2nifti.convert_directory(dicom_path, temp_nifti_dir)

    shape_out = get_shape_from_nifties(temp_nifti_dir)

    shutil.rmtree(temp_nifti_dir)

    return shape_out


def create_empty_seg(
    batch_path: str, output_dir: str, nifti_dir: str = "", dicom_dir: str = ""
):

    if nifti_dir == "" and dicom_dir == "":
        raise ValueError(
            "No nifti directory or dicom directory provided for the reference of empty segmentation file. Please \
                provide valid base_nifti_dir or dicom input_dir."
        )

    # Gather the input batch directories from the dicom images
    batch_dirs = [f for f in glob.glob(os.path.join(batch_path, "*"))]

    # Process each batch directory
    for batch_element in batch_dirs:
        output_path = os.path.join(batch_element, output_dir)
        output_nifites = get_all_files_from_dir(
            output_path, filter_pattern=r".*\.nii.*"
        )
        if len(output_nifites) > 0:
            continue

        if nifti_dir != "":
            target_path = os.path.join(batch_element, nifti_dir)
            empty_seg_shape, empty_seg_dtype, base_nifti = get_shape_from_nifties(
                target_path
            )
        else:
            target_path = os.path.join(batch_element, dicom_dir)
            empty_seg_shape, empty_seg_dtype, base_nifti = get_shape_from_dicoms(
                target_path
            )

        empty_seg_np = np.zeros(empty_seg_shape, dtype=empty_seg_dtype)

        empty_seg_nifti = nib.Nifti1Image(
            empty_seg_np, base_nifti.affine, base_nifti.header
        )

        empty_seg_output_file = os.path.join(output_path, "empty.nii.gz")
        nib.save(empty_seg_nifti, empty_seg_output_file)

    return
