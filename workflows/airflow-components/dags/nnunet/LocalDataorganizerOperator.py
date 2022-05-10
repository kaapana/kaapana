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
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalDataorganizerOperator(KaapanaPythonBaseOperator):
    def get_json(self, filename, json_list):

        if len(json_list) == 1:
            return json_list[0]
        elif len(json_list) > 1:
            filter_id = basename(filename).replace(".nii.gz", "").replace("_combination_","-")
            print(f"# filter_id: {filter_id}")
            json_file_filtered = [json_file for json_file in json_list if filter_id in json_file]
            ensemble_file_filtered = [json_file for json_file in json_list if "ensemble_seg_info.json" in json_file]
            if len(ensemble_file_filtered) > 0:
                return ensemble_file_filtered[0]
                
            if len(json_file_filtered) > 0:
                return json_file_filtered[0]
            else:
                print(f"# No fitting json could be identified!")
                print(f"# Filename: {filename}")
                print(json.dumps(json_list, indent=4, sort_keys=True, default=str))
                return None
        else:
            return None

    def get_batch_element(self, filename, batch_path):
        print(f"# batch_path: {batch_path}")
        print(f"# filename: {filename}")
        filter_id = basename(filename).replace(".nii.gz","").split("_")[0]
        search_term = join(batch_path,"*", "dcm-converter-ct", f"{filter_id}*.nii*")
        print(f"# search_term: {search_term}")
        nifti_files = sorted(glob(search_term, recursive=False))
        print(f"# nifti_files: {nifti_files}")

        print(f"# filter_id: {filter_id}")
        nifti_filtered = [dirname(dirname(nifti_file)) for nifti_file in nifti_files if f"{filter_id}" in nifti_file]
        print(f"# get_batch_element nifti_filtered: {nifti_filtered}")
        if len(nifti_filtered) == 1:
            return nifti_filtered[0]
        else:
            return None

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
        assert self.origin in ["batch", "batchelement"]
        assert self.target in ["batch", "batchelement"]

        run_dir = os.path.join(self.workflow_dir, kwargs['dag_run'].run_id)
        if self.origin == "batch":
            iter_dirs = [run_dir]
        elif self.origin == "batchelement":
            iter_dirs = sorted([f for f in glob(os.path.join(run_dir, self.batch_name, '*'))])

        print(f"# Found {len(iter_dirs)} iter_dirs")
        model_id = 0
        for iter_dir in iter_dirs:
            print(f"# processing iter_dir: {iter_dir}")
            model_id += 1

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

                file_id =  basename(nifti_file).replace(".nii.gz", f"-{model_id}")
                target_file_path = join(target_dir,f"{file_id}.nii.gz")
                print(f"# copy NIFTI: {nifti_file} -> {target_file_path}")
                shutil.copy2(nifti_file, target_file_path)
                processed_count += 1

                json_file = self.get_json(filename=nifti_file, json_list=json_files)
                if json_file is not None:
                    target_json_path = join(target_dir, basename(json_file).replace(".json",f"-{model_id}.json"))
                    print(f"# copy JSON: {json_file} -> {target_json_path}")
                    shutil.copy2(json_file, target_json_path)
                else:
                    print(f"# No json found!")
                    raise ValueError('ERROR')
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
            # exit(1)
        else:
            print("# DONE #")

    def __init__(self,
                 dag,
                 mode,  # batch2batch,batchelement2batchelement,batch2batchelement,batchelement2batch
                 target_batchname=None,
                 batch_name=None,
                 workflow_dir=None,
                 parallel_id=None,
                 **kwargs):

        self.origin = mode.split("2")[0]
        self.target = mode.split("2")[1]
        self.target_batchname = target_batchname

        super().__init__(
            dag=dag,
            name="do",
            python_callable=self.start,
            batch_name=batch_name,
            parallel_id=parallel_id,
            workflow_dir=workflow_dir,
            execution_timeout=timedelta(minutes=20),
            **kwargs
        )
