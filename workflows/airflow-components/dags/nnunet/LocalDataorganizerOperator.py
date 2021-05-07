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

        copy_target_data = True

        print("# LocalDataorganizerOperator started ...")
        print(f"# workflow_dir {self.workflow_dir}")
        run_dir = os.path.join(self.workflow_dir, kwargs['dag_run'].run_id)

        processed_count = 0

        if self.ensemble_dir != None:
            self.ensemble_dir = join(run_dir, self.ensemble_dir)
            if not exists(self.ensemble_dir):
                print("# Could not find ensemble_pred_dir !")
                print(f"# pred: {self.ensemble_dir}")
                exit(1)

        batch_folders = [f for f in glob(os.path.join(run_dir, self.batch_name, '*'))]
        print("# Found {} batches".format(len(batch_folders)))
        nnunet_cohort_dir = join(run_dir, "nnunet-cohort")
        model_counter = 0
        for batch_element_dir in batch_folders:
            print(f"# processing batch-element: {batch_element_dir}")
            model_counter += 1
            single_model_pred_dir = join(batch_element_dir, self.operator_in_dir)
            single_model_pred_files = sorted(glob(join(single_model_pred_dir, "*.nii*"), recursive=False))
            seg_info_json = glob(join(single_model_pred_dir, "*.json*"), recursive=False)
            assert len(seg_info_json) == 1
            seg_info_json = seg_info_json[0]

            for single_model_pred_file in single_model_pred_files:
                single_model_pred_filename = basename(single_model_pred_file)
                target_filename = f"{basename(single_model_pred_file).replace('.nii.gz','')}_model_{model_counter}.nii.gz"
                target_file_id = target_filename.replace(".nii.gz","")

                search_string = join(nnunet_cohort_dir, "**", single_model_pred_filename)
                nnunet_cohort_files = sorted(glob(search_string, recursive=True))
                print(f"# found: {len(nnunet_cohort_files)} files @ {search_string}")
                assert len(nnunet_cohort_files) == 1
                nnunet_cohort_seg_found = nnunet_cohort_files[0]
                print(f"# using: {nnunet_cohort_seg_found}")
                target_batch_element_dir=dirname(dirname(nnunet_cohort_seg_found))
                print(f"# target_batch_element_dir: {target_batch_element_dir}")

                ensemble_file = join(self.ensemble_dir, single_model_pred_filename)
                print(f"# ensemble_file: {ensemble_file}")
                
                target_single_model = join(target_batch_element_dir, "nnunet-inference", target_filename)
                target_single_model_info = join(target_batch_element_dir, "nnunet-inference", f"{target_file_id}.json")
                
                target_ensemble = join(target_batch_element_dir, "nnunet-ensemble", basename(single_model_pred_file)).replace(".nii.gz","_ensemble.nii.gz")
                target_ensemble_info = join(target_batch_element_dir, "nnunet-ensemble", basename(single_model_pred_file).replace(".nii.gz","_ensemble.json"))
                Path(dirname(target_single_model)).mkdir(parents=True, exist_ok=True)
                Path(dirname(target_ensemble)).mkdir(parents=True, exist_ok=True)

                print(f"#")
                print(f"# target_single_model: {target_single_model}")
                print(f"#")
                print(f"# target_ensemble: {target_ensemble}")
                print(f"#")
                assert not exists(target_single_model) and not exists(target_single_model_info)

                shutil.copy2(seg_info_json, target_single_model_info)
                if copy_target_data:
                    shutil.copy2(single_model_pred_file, target_single_model)
                else:
                    shutil.move(single_model_pred_file, target_single_model)

                if not exists(target_ensemble):
                    print(f"# target_ensemble not found -> copy")
                    shutil.copy2(seg_info_json, target_ensemble_info)
                    if copy_target_data:
                        shutil.copy2(single_model_pred_file, target_single_model)
                        shutil.copy2(ensemble_file, target_ensemble)
                    else:
                        shutil.move(single_model_pred_file, target_single_model)
                        shutil.move(ensemble_file, target_ensemble)
                else:
                    print(f"# target_ensemble already present -> skipping")
                
                processed_count += 1
                print("##################################################")

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
                 gt_operator,
                 ensemble_operator,
                 batch_name=None,
                 workflow_dir=None,
                 *args,
                 **kwargs):

        self.gt_dir = gt_operator.operator_out_dir
        self.ensemble_dir = ensemble_operator.operator_out_dir if ensemble_operator != None else None

        super().__init__(
            dag,
            name="data-organizer",
            python_callable=self.start,
            batch_name=batch_name,
            workflow_dir=workflow_dir,
            execution_timeout=timedelta(minutes=20),
            *args,
            **kwargs
        )
