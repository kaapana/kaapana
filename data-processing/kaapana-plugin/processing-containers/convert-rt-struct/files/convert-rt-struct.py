import os
from glob import glob
from os import getenv
from os.path import exists, join

from dcmrtstruct2nii import dcmrtstruct2nii
import SimpleITK as sitk

if __name__ == "__main__":
    workflow_dir = getenv("WORKFLOW_DIR", None)
    if not exists(workflow_dir):
        # Workaround if this is being run in dev-server
        workflow_dir_dev = workflow_dir.split("/")
        workflow_dir_dev.insert(3, "workflows")
        workflow_dir_dev = "/".join(workflow_dir_dev)

        if not exists(workflow_dir_dev):
            raise Exception(f"Workflow directory {workflow_dir} does not exist!")

        workflow_dir = workflow_dir_dev

    batch_name = getenv("BATCH_NAME", "batch")
    assert exists(
        join(workflow_dir, batch_name)
    ), f"Batch directory {join(workflow_dir, batch_name)} does not exist!"

    operator_in_dir = getenv("OPERATOR_IN_DIR", None)
    assert operator_in_dir is not None, "Operator input directory not specified!"

    org_image_input_dir = getenv("ORIG_IMAGE_OPERATOR_DIR", None)
    assert (
        org_image_input_dir is not None
    ), "Original image input directory not specified!"

    operator_out_dir = getenv("OPERATOR_OUT_DIR", None)
    assert operator_out_dir is not None, "Operator output directory not specified!"

    batch_folders = sorted([f for f in glob(join("/", workflow_dir, batch_name, "*"))])
    for batch_element_dir in batch_folders:
        dicom_image_dir = os.path.join(
            workflow_dir, batch_name, batch_element_dir, operator_in_dir
        )
        rtstruct_dir = os.path.join(
            workflow_dir, batch_name, batch_element_dir, org_image_input_dir
        )
        output_dir = os.path.join(
            workflow_dir, batch_name, batch_element_dir, operator_out_dir
        )

        dcmrtstruct2nii(
            join(dicom_image_dir, os.listdir(dicom_image_dir)[0]),
            rtstruct_dir,
            output_dir,
        )

        # load image using SimpleITK and save it as NIfTI in the output directory as reference_image.nii.gz
        # reader = sitk.ImageSeriesReader()
        # dicom_names = reader.GetGDCMSeriesFileNames(rtstruct_dir)
        # reader.SetFileNames(dicom_names)
        # image = reader.Execute()
        # sitk.WriteImage(image, os.path.join(output_dir, "reference_image.nii.gz"))
