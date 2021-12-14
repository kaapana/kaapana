import os
import glob
import json
import shutil
import pydicom
import numpy as np
import nibabel as nib
from os.path import join, basename, dirname, exists
from os import remove
from pathlib import Path
from datetime import timedelta
from multiprocessing.pool import ThreadPool
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalSegCheckOperator(KaapanaPythonBaseOperator):

    def get_nifti_dimensions(self, input_dir, check_labels=True):
        input_files = sorted(glob.glob(join(input_dir, "**", "*.nii*"), recursive=True))
        # print(f"Check for NIFTI at {input_dir}: found {len(input_files)} files.")
        if len(input_files) == 0:
            return [input_dir]

        nifti_path = input_files[0]
        img = nib.load(nifti_path)
        x, y, z = img.shape

        if check_labels and np.max(img.get_fdata()) == 0:
            print("# ")
            print("# ")
            print(f"# Could not find any label in {nifti_path}!")
            print("# ABORT")
            print("# ")
            print("# ")

            return [input_dir]

        return [input_dir, [x, y, z]]

    def get_dicom_dimensions(self, input_dir, check_labels=True):
        input_files = sorted(glob.glob(join(input_dir, "**", "*.dcm"), recursive=True))
        # print(f"Check for DICOM at {input_dir}: found {len(input_files)} files.")
        if len(input_files) == 0:
            return [input_dir]

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
            numberOfFrames = len(next(os.walk(dirname(dcm_path)))[2])
        else:
            print("# ")
            print("# ")
            print("# Could not extract DICOM dimensions!")
            print(f"# File: {dcm_path}")
            print(f"# Dimensions: {data.shape}")
            print("# ")
            print("# ")
            return [input_dir]

        x, y, z = rows, columns, numberOfFrames

        return [input_dir, [x, y, z]]

    def start(self, ds, **kwargs):
        print("# Check files started...")

        case_count = 0
        ignored_cases = []
        run_dir = join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folders = sorted([f for f in glob.glob(join(run_dir, BATCH_NAME, '*'))])
        output_dir = join(run_dir, self.operator_out_dir)

        print("# Found {} batches".format(len(batch_folders)))

        input_dirs = [dir.operator_out_dir for dir in self.input_operators]
        print(f"# Processing input dirs: {input_dirs}")

        for batch_element_dir in batch_folders:
            print("# ")
            print("##############################################################################################################")
            print("# ")
            print(f"# Testing: {batch_element_dir.split('/')[-1]}")
            print("# ")
            dimensions_list = []
            input_dirs_complete = [join(batch_element_dir, dir) for dir in input_dirs]

            dcm_results = ThreadPool(self.parallel_checks).imap_unordered(self.get_dicom_dimensions, input_dirs_complete)

            nifti_check_list = []
            for dcm_result in dcm_results:
                if len(dcm_result) == 2:
                    dimensions_list.append(dcm_result[1])
                else:
                    nifti_check_list.append(dcm_result[0])

            if len(nifti_check_list) > 0:
                nifti_results = ThreadPool(self.parallel_checks).imap_unordered(self.get_nifti_dimensions, nifti_check_list)

                for nifti_result in nifti_results:
                    if len(nifti_result) == 2:
                        dimensions_list.append(nifti_result[1])
                    else:
                        dimensions_list.append(None)
                        print("# ")
                        print(f"# Could not extract dimensions: {nifti_check_list[0]}")
                        print("# ")

            last_dimension = None
            error = False

            i = 0
            for i in range(0, len(dimensions_list)):
                dimension = dimensions_list[i]
                if dimension == None:
                    error = True
                    continue
                if last_dimension != None:
                    if dimension != last_dimension:
                        error = True
                        print("# ")
                        print(f"# {input_dirs[i-1]} vs {input_dirs[i]}: {last_dimension} <-> {dimension}: ERROR")
                        print("# ERROR: Dimensions are different!!!")
                        print("# ")
                        if self.anonymize:
                            file_id = case_count
                            case_count +=1
                        else:
                            file_id = basename(batch_element_dir)

                        ignored_cases.append(f"{file_id}: {input_dirs[i-1]} vs {input_dirs[i]}: {last_dimension} <-> {dimension}: ERROR")
                    else:
                        print(f"{input_dirs[i-1]} vs {input_dirs[i]}: {last_dimension} <-> {dimension}: OK")

                last_dimension = dimension

            if error:
                if self.move_data:
                    target_dir = batch_element_dir.replace(BATCH_NAME, "dimension_issue")
                    print("# ")
                    print("# Moving batch-data:")
                    print(f"{batch_element_dir} -> {target_dir}")
                    print("# ")
                    shutil.move(batch_element_dir, target_dir)
                if self.abort_on_error:
                    exit(1)

        print("# ")
        if len(ignored_cases) > 0:
            print("# ")
            print(f"# Got {len(ignored_cases)} ignored cases -> writing log-file!")
            print("# ")
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            log_path = join(output_dir, "log_ignored_cases.txt")
            with open(log_path, 'w') as f:
                for item in ignored_cases:
                    f.write("%s\n" % item)
        print("# ")
        print("# DONE ")
        print("# ")

    def __init__(self,
                 dag,
                 input_operators,
                 move_data=True,
                 abort_on_error=False,
                 anonymize=True,
                 parallel_checks=3,
                 **kwargs):

        self.abort_on_error = abort_on_error
        self.move_data = move_data
        self.anonymize = anonymize
        self.input_operators = input_operators
        self.parallel_checks = parallel_checks

        super().__init__(
            dag=dag,
            name="check-seg-data",
            python_callable=self.start,
            execution_timeout=timedelta(minutes=60),
            **kwargs
        )
