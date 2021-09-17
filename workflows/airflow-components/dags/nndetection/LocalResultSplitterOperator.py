import os
import shutil
import json
import numpy as np
import nibabel as nib
from datetime import timedelta
from multiprocessing.pool import ThreadPool
from glob import glob
from pathlib import Path
from os.path import join, basename, dirname, exists
from shutil import move
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalResultSplitterOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):
        processed_count = 0

        print("# Result splitter started")
        print("#")
        print(f"# operator_out_dir: {self.operator_out_dir}")
        print(f"# operator_in_dir: {self.operator_in_dir}")
        print("#")
        print("#")
        batch_name = "batch"
        run_dir = join(self.workflow_dir, kwargs['dag_run'].run_id)

        batch_folders = sorted([f for f in glob(join('/', run_dir, batch_name, '*'))])
        for batch_element_dir in batch_folders:
            print("#")
            print(f"# Processing batch-element {batch_element_dir}")
            print("#")
            element_input_dir = join(batch_element_dir, self.operator_in_dir)
            element_output_dir = join(batch_element_dir, self.operator_out_dir)

            # check if input dir present
            if not exists(element_input_dir):
                print("#")
                print(f"# Input-dir: {element_input_dir} does not exists!")
                print("# -> skipping")
                print("#")
                continue

            # creating output dir
            Path(element_output_dir).mkdir(parents=True, exist_ok=True)

            # creating output dir
            seg_info_json = [k for k in glob(join(element_input_dir, "*.json")) if '_measurements' not in k]
            assert len(seg_info_json) == 1

            measurement_json = [k for k in glob(join(element_input_dir, "*.json")) if '_measurements' in k]
            assert len(measurement_json) == 1

            target_measurements = join(element_output_dir, basename(measurement_json[0]))
            print("# Found:")
            print(f"{seg_info_json=}")
            print(f"{measurement_json=}")
            print(f"{measurement_json[0]} --> {target_measurements}")
            print("#")

            move(measurement_json[0], target_measurements)
            move(seg_info_json[0], seg_info_json[0].replace(basename(seg_info_json[0]), "seg_info.json"))
            processed_count += 1

        print("# ")
        print("#")
        print(f"# Processed file_count: {processed_count}")
        print("#")
        print("#")
        if processed_count == 0:
            print("#")
            print("##################################################")
            print("#")
            print("#################  ERROR  #######################")
            print("#")
            print("# ----> NO FILES HAVE BEEN PROCESSED!")
            print("#")
            print("##################################################")
            print("#")
            exit(1)
        else:
            print("# DONE #")

    def __init__(self,
                 dag,
                 *args,
                 **kwargs):

        super().__init__(
            dag,
            name="result_splitter",
            python_callable=self.start,
            execution_timeout=timedelta(minutes=1),
            *args,
            **kwargs
        )
