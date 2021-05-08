import os
import shutil
import numpy as np
import nibabel as nib
from datetime import timedelta
from multiprocessing.pool import ThreadPool
from glob import glob
from pathlib import Path
from os.path import join, basename, dirname, exists
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalDataorganizerOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):
        processed_count = 0

        print("# LocalDataorganizerOperator tarted ...")
        print("#")
        print(f"# origin:     {self.origin}")
        print(f"# target:     {self.target}")
        print("#")
        print(f"# operator_out_dir: {self.operator_out_dir}")
        print(f"# operator_in_dir: {self.operator_in_dir}")
        print("#")
        print(f"# batch_name: {self.batch_name}")
        print(f"# target_batchname: {self.target_batchname}")
        print("#")
        print("#")
        assert self.origin in ["batch","batchelement"]
        assert self.target in ["batch","batchelement"]
        
        run_dir = os.path.join(self.workflow_dir, kwargs['dag_run'].run_id)
        if self.origin == "batch":
            iter_dirs = [run_dir]
        elif self.origin == "batchelement":
            iter_dirs = sorted([f for f in glob(os.path.join(run_dir, self.batch_name, '*'))])

        print(f"# Found {len(iter_dirs)} iter_dirs")
        for iter_dir in iter_dirs:
            print(f"# processing iter_dir: {iter_dir}")

            input_dir = join(iter_dir, self.operator_in_dir)
            nifti_files = sorted(glob(join(input_dir, "*.nii*"), recursive=False))
            json_files = sorted(glob(join(input_dir, "*.json"), recursive=False))

            for nifti_file in nifti_files:
                if self.target == "batch":
                    target_dir = join(run_dir, self.operator_out_dir)
                elif self.target == "batchelement":
                    target_batch_element = self.get_batch_element(filename=nifti_file, batch_path=join(run_dir, self.target_batchname))
                    assert target_batch_element != None
                    target_dir = join(target_batch_element, self.operator_out_dir)
                Path(target_dir).mkdir(parents=True, exist_ok=True)

                target_file_path = join(target_dir, basename(nifti_file))
                print(f"# copy NIFTI: {nifti_file} -> {target_file_path}")
                shutil.copy2(nifti_file, target_file_path)
                processed_count += 1

                json_file = self.get_json(filename=nifti_file, json_list=json_files)
                if json_file is not None:
                    if basename(json_file) == "model_combinations.json":
                        print("# Ensemble detected -> searching nnunet-predict seg-info...")
                        inference_json_list = sorted(glob(join(target_batch_element, "nnunet-inference", "*.json"), recursive=False))
                        inference_json = self.get_json(filename=nifti_file, json_list=inference_json_list)
                        assert inference_json != None
                        target_json_path = join(target_dir, basename(inference_json))
                        print(f"# copy JSON inference -> ensemble: {target_json_path} -> {target_json_path}")
                        shutil.copy2(json_file, target_json_path)

                    target_json_path = join(target_dir, basename(json_file))
                    print(f"# copy JSON: {json_file} -> {target_json_path}")
                    shutil.copy2(json_file, target_json_path)
                else:
                    print(f"# No json found!")
                    exit(1)
                print(f"#")
            print(f"#")

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
                 mode,  # batch2batch,batchelement2batchelement,batch2batchelement,batchelement2batch
                 target_batchname=None,
                 batch_name=None,
                 workflow_dir=None,
                 parallel_id=None,
                 *args,
                 **kwargs):

        self.origin = mode.split("2")[0]
        self.target = mode.split("2")[1]
        self.target_batchname = target_batchname

        super().__init__(
            dag,
            name="do",
            python_callable=self.start,
            batch_name=batch_name,
            parallel_id=parallel_id,
            workflow_dir=workflow_dir,
            execution_timeout=timedelta(minutes=20),
            *args,
            **kwargs
        )
