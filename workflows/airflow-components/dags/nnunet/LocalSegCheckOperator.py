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

    def get_nifti_dimensions(self, input_dir, check_labels=True):
        input_files = sorted(glob.glob(os.path.join(input_dir, "**", "*.nii*"), recursive=True))
        if len(input_files) == 0:
            return None

        nifti_path = input_files[0]
        img = nib.load(nifti_path)
        x, y, z = img.shape

        if check_labels and np.max(img.get_fdata()) == 0:
            print("Could not find any label in {}!".format(nifti_path))
            print("ABORT")
            exit(1)

        return [x, y, z]

    def get_dicom_dimensions(self, input_dir, check_labels=True):
        input_files = sorted(glob.glob(os.path.join(input_dir, "**", "*.dcm"), recursive=True))
        if len(input_files) == 0:
            return None

        dcm_path = input_files[0]

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
        print("Check files started...")

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folders = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]

        print("Found {} batches".format(len(batch_folders)))

        input_dirs = [dir for dir in self.input_operators.operator_out_dir]
        print(f"Processing input dirs: {input_dirs}")

        for batch_element_dir in batch_folders:
            for input_dir in input_dirs:
                input_path = os.path.join(batch_element_dir,input_dir)

                dimensions = self.get_dicom_dimensions(input_path)
                dimensions = self.get_nifti_dimensions(input_path) if dimensions is None else dimensions

                if dimensions is None:
                    print("")
                    print(f"Could not extract dimensions: {input_path}")
                    print("")
                    exit(1)

            last_dimension = None
            for dimension in dimensions:
                if last_dimension != None:
                    if dimension != last_dimension:
                        print("#######################################################")
                        print("")
                        print("  Dimensions are different!!!")
                        print(f" Series: {batch_element_dir}")
                        print("")
                        print("#######################################################")
                        if self.move_data:
                            target_dir = batch_element_dir.replace(BATCH_NAME, "dimension_issue")
                            print(f"Moving batch-data to {target_dir}")
                            shutil.move(batch_element_dir, target_dir)
                        if self.abort_on_error:
                            exit(1)
                    else:
                        print(f"{input.split('/')[-1]}: Dimensions ok!")
                    
                last_dimension = dimension

        print("")

    def __init__(self,
                 dag,
                 input_operators,
                 abort_on_error=False,
                 move_data=True,
                 *args,
                 **kwargs):

        self.abort_on_error = abort_on_error
        self.move_data = move_data
        self.input_operators = input_operators

        super().__init__(
            dag,
            name="check-seg-data",
            python_callable=self.start,
            *args,
            **kwargs
        )
