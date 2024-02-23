import os
import json
import glob
import nibabel as nib
import numpy as np
import re

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


def ensure_dir(target: str):
    """
    Ensure that the specified directory path exists; if not, create it.

    Parameters:
    - target (str): The directory path to ensure existence for.
    """
    if not os.path.exists(target):
        os.makedirs(target)


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


class LocalCreateEmptySegmentsOperator(KaapanaPythonBaseOperator):
    """
    Operator to List all the niftis in the provided directory and create seg_info.json from
    their filename and segmentation labels.

    **Inputs:**

        * input directory / input operator to get base nifti
        * operator_out_dir where it will create the empty segment
        * check_if_segmentation_exists (boolean): An optional boolean variable that will check if
            any other nifti file exists on the output directory and if found it will
            skip creation of new empty segmentation.

    **Outputs**

        *
    """

    def start(self, ds, **kwargs):
        print("Starting module LocalCreateEmptySegmentsOperator...")
        print(kwargs)

        self.run_id = kwargs["dag_run"].run_id

        # Define input directories from the minio files workflow
        run_dir = os.path.join(self.airflow_workflow_dir, self.run_id)

        # Gather the input batch directories from the dicom images
        batch_dirs = [f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))]

        # Process each batch directory
        for batch_element in batch_dirs:
            input_dir = os.path.join(batch_element, self.operator_in_dir)
            output_dir = os.path.join(batch_element, self.operator_out_dir)

            output_nifites = get_all_files_from_dir(
                output_dir, filter_pattern=r".*\.nii.*"
            )
            if not self.forced and len(output_nifites) > 0:
                continue

            # Retrieve all files in the input directory matching the NIfTI file format
            all_nifties = get_all_files_from_dir(input_dir, filter_pattern=r".*\.nii.*")

            if len(all_nifties) == 0:
                raise FileNotFoundError(
                    "No nifti file found in the directory {} to be used as a base nifti for empty segmentation file".format(
                        input_dir
                    )
                )

            base_nifti = nib.load(all_nifties[0])
            base_nifti_np = np_from_nifti(all_nifties[0])
            empty_seg_np = np.zeros(base_nifti_np.shape, dtype=base_nifti_np.dtype)
            # empty_seg_np = np.full(base_nifti_np.shape, 0, dtype=int)

            empty_seg_nifti = nib.Nifti1Image(
                empty_seg_np, base_nifti.affine, base_nifti.header
            )

            empty_seg_output_file = os.path.join(output_dir, "empty.nii.gz")
            nib.save(empty_seg_nifti, empty_seg_output_file)

        return

    def __init__(
        self,
        dag,
        name="create-empty-segmentation",
        forced: bool = False,
        **kwargs,
    ):
        self.forced = forced
        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
