import os
import glob
import numpy as np
import nibabel as nib
import pydicom
import json

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalSegCheckOperator(KaapanaPythonBaseOperator):

    def get_nifti_dimensions(self, nifti_path):
        x, y, z = nib.load(nifti_path).shape
        return [x, y, z]

    def get_dicom_dimensions(self, dcm_path):
        data = pydicom.dcmread(dcm_path).pixel_array
        file_count = len(next(os.walk(os.path.dirname(dcm_path)))[2])
        x, y = data.shape
        return [x, y, file_count]

    def start(self, ds, **kwargs):
        print("Split-Labels started..")

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folders = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]

        print("Found {} batches".format(len(batch_folders)))

        for batch_element_dir in batch_folders:
            nifti_input_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            dcm_input_dir = os.path.join(batch_element_dir, self.self.dicom_input_operator.operator_out_dir)
            
            batch_nifti_files = sorted(glob.glob(os.path.join(nifti_input_dir, "**", "*.nii*"), recursive=True))
            print("Found {} NIFTI files at {}.".format(len(batch_nifti_files),nifti_input_dir))
            
            batch_dcm_files = sorted(glob.glob(os.path.join(dcm_input_dir, "**", "*.dcm*"), recursive=True))
            print("Found {} DICOM files at {}.".format(len(batch_dcm_files),dcm_input_dir))
            
            if len(batch_nifti_files) == 0:
                print("No NIFTI file was found!")
                print("abort!")
                exit(1)

            if len(batch_dcm_files) == 0:
                print("No DICOM file was found!")
                print("abort!")
                exit(1)

            print("Loading DICOM...")
            dicom_dimensions = self.get_dicom_dimensions(dcm_path=batch_dcm_files[0])

            print("Loading NIFTIs...")
            for nifti in batch_nifti_files:
                nifti_dimensions = self.get_nifti_dimensions(nifti_path=nifti)

                if dicom_dimensions != nifti_dimensions:
                    print("Dimensions are different!!!")
                    exit(1)
                else:
                    print(f"{nifti}: Dimensions ok!")


    def __init__(self,
                 dag,
                 dicom_input_operator,
                 *args,
                 **kwargs):
        
        self.dicom_input_operator = dicom_input_operator

        super().__init__(
            dag,
            name="check-seg-data",
            python_callable=self.start,
            *args,
            **kwargs
        )
