import os
import glob
import json
import shutil
import pydicom
import numpy as np
import nibabel as nib

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalSegCheckOperator(KaapanaPythonBaseOperator):

    def get_nifti_dimensions(self, nifti_path, check_labels=True):
        img = nib.load(nifti_path)
        x, y, z = img.shape

        if check_labels and np.max(img.get_fdata()) == 0:
            print("Could not find any label in {}!".format(nifti_path))
            print("ABORT")
            exit(1)

        return [x, y, z]

    def get_dicom_dimensions(self, dcm_path, check_labels=True):
        data = pydicom.dcmread(dcm_path)
        # labels = data.BodyPartExamined
        columns = data.Columns
        rows = data.Rows
        if data.Modality == "SEG" and hasattr(data, 'NumberOfFrames'):
            numberOfFrames = data.NumberOfFrames
            label_count = len(data.SegmentSequence)
            numberOfFrames //= label_count
        elif not hasattr(data, 'NumberOfFrames'):
            numberOfFrames = len(next(os.walk(os.path.dirname(dcm_path)))[2])
        else:
            print("")
            print("")
            print("Could not extract DICOM dimensions!")
            print(f"File: {dcm_path}")
            print(f"Dimensions: {data.shape}")
            print("")
            print("")
            exit(1)

        x, y, z = rows, columns, numberOfFrames

        return [x, y, z]

    def start(self, ds, **kwargs):
        print("Check SEG files started..")

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folders = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]

        print("Found {} batches".format(len(batch_folders)))

        for batch_element_dir in batch_folders:
            nifti_input_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            dcm_input_dir = os.path.join(batch_element_dir, self.dicom_input_operator.operator_out_dir)

            batch_input_files = sorted(glob.glob(os.path.join(nifti_input_dir, "**", "*.nii*"), recursive=True))
            print("Found {} NIFTI files at {}.".format(len(batch_input_files), nifti_input_dir))
            if len(batch_input_files) == 0:
                print("No NIFTI file was found -> checking for DICOM SEG...")
                batch_input_files = sorted(glob.glob(os.path.join(nifti_input_dir, "**", "*.dcm*"), recursive=True))
                print("Found {} DICOM SEG files at {}.".format(len(batch_input_files), nifti_input_dir))
                if len(batch_input_files) == 0:
                    print("")
                    print("No DICOM SEG file was found -> abort!")
                    print("")
                    exit(1)

            batch_dcm_files = sorted(glob.glob(os.path.join(dcm_input_dir, "**", "*.dcm*"), recursive=True))
            print("Found {} DICOM files at {}.".format(len(batch_dcm_files), dcm_input_dir))

            if len(batch_dcm_files) == 0:
                print("No DICOM file was found!")
                print("abort!")
                exit(1)

            print("Loading DICOM...")
            dicom_dimensions = self.get_dicom_dimensions(dcm_path=batch_dcm_files[0])

            print("Loading Input files...")
            for input in batch_input_files:
                if ".dcm" in input:
                    print("Loading DICOM dimensions...")
                    input_dimensions = self.get_dicom_dimensions(dcm_path=input)
                elif ".nii" in input:
                    print("Loading NIFTI dimensions...")
                    input_dimensions = self.get_nifti_dimensions(nifti_path=input)
                else:
                    print(f"Unexpected file: {input} !")
                    print("abort.")
                    print("")
                    exit(1)

                print(f"Dimensions INPUT {input.split('/')[-1]}: {input_dimensions}")
                print(f"Dimensions DICOM {batch_dcm_files[0].split('/')[-1]}: {dicom_dimensions}")
                print("")
                if dicom_dimensions != input_dimensions:
                    print("#######################################################")
                    print("")
                    print("  Dimensions are different!!!")
                    print("")
                    print("#######################################################")
                    if self.abort_on_error:
                        exit(1)
                    else:
                        target_dir = batch_element_dir.replace(BATCH_NAME, "dimension_issue")
                        print(f"Moving batch-data to {target_dir}")
                        shutil.move(batch_element_dir, target_dir)

                else:
                    print(f"{input.split('/')[-1]}: Dimensions ok!")
                print("")

    def __init__(self,
                 dag,
                 dicom_input_operator,
                 abort_on_error=False,
                 *args,
                 **kwargs):

        self.abort_on_error = abort_on_error
        self.dicom_input_operator = dicom_input_operator

        super().__init__(
            dag,
            name="check-seg-data",
            python_callable=self.start,
            *args,
            **kwargs
        )
