import os
import glob
import nibabel as nib
import numpy as np

from .handle import get_all_files_from_dir, np_from_nifti


def create_empty_seg(batch_path: str, input_dir: str, output_dir: str):
    # Gather the input batch directories from the dicom images
    batch_dirs = [f for f in glob.glob(os.path.join(batch_path, "*"))]

    # Process each batch directory
    for batch_element in batch_dirs:
        input_path = os.path.join(batch_element, input_dir)
        output_path = os.path.join(batch_element, output_dir)

        output_nifites = get_all_files_from_dir(
            output_path, filter_pattern=r".*\.nii.*"
        )
        if len(output_nifites) > 0:
            continue

        # Retrieve all files in the input directory matching the NIfTI file format
        all_nifties = get_all_files_from_dir(input_path, filter_pattern=r".*\.nii.*")

        if len(all_nifties) == 0:
            raise FileNotFoundError(
                "No nifti file found in the directory {} to be used as a base nifti for empty segmentation file.".format(
                    input_path
                )
                + "Provide base_nifti_dir parameter to avoid such errors"
            )

        base_nifti = nib.load(all_nifties[0])
        base_nifti_np = np_from_nifti(all_nifties[0])
        empty_seg_np = np.zeros(base_nifti_np.shape, dtype=base_nifti_np.dtype)
        # empty_seg_np = np.full(base_nifti_np.shape, 0, dtype=int)

        empty_seg_nifti = nib.Nifti1Image(
            empty_seg_np, base_nifti.affine, base_nifti.header
        )

        empty_seg_output_file = os.path.join(output_path, "empty.nii.gz")
        nib.save(empty_seg_nifti, empty_seg_output_file)

    return
