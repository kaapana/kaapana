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

        print("# Evaluating predictions started ...")
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
        for batch_element_dir in batch_folders:
            print(f"# processing batch-element: {batch_element_dir}")
            single_model_pred_dir = join(batch_element_dir, self.operator_in_dir)
            single_model_pred_files = sorted(glob(join(single_model_pred_dir, "*.nii*"), recursive=False))
            for single_model_pred_file in single_model_pred_files:
                cohort_target_dir = join(run_dir, "nnunet-cohort", basename(single_model_pred_file).replace(".nii.gz", ""))

                single_model_target = join(cohort_target_dir,"single-model-prediction",basename(single_model_pred_file))
                ensemble_target = join(cohort_target_dir,"ensemble-prediction",basename(single_model_pred_file))
                Path(dirname(single_model_target)).mkdir(parents=True, exist_ok=True)
                Path(dirname(ensemble_target)).mkdir(parents=True, exist_ok=True)

                ensemble_file = join(self.ensemble_dir, basename(single_model_pred_file))
                if copy_target_data:
                    shutil.copy2(single_model_pred_file, single_model_target)
                    shutil.copy2(ensemble_file, ensemble_target)
                else:
                    shutil.move(single_model_pred_file, single_model_target)
                    shutil.move(ensemble_file, ensemble_target)
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
