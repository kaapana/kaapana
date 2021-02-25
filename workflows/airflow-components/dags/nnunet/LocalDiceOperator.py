import os
import numpy as np
import nibabel as nib
from datetime import timedelta
from multiprocessing.pool import ThreadPool
from glob import glob
from os.path import join, basename, dirname, exists
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalDiceOperator(KaapanaPythonBaseOperator):
    def calc_dice(self, pred, gt, empty_score=1.0):
        print(f"# loading gt:   {gt}")
        print(f"# loading pred: {pred}")
        pred = nib.load(pred).get_fdata()
        gt = nib.load(gt).get_fdata()

        pred = np.asarray(pred).astype(bool)
        gt = np.asarray(gt).astype(bool)

        if pred.shape != gt.shape:
            print("#")
            print("##################################################")
            print("#")
            print("#################  ERROR  #######################")
            print("#")
            print("# ----> SHAPE MISMATCH!")
            print(f"# gt:   {gt.shape}")
            print(f"# pred: {pred.shape}")
            print("#")
            print("#")
            print("##################################################")
            print("#")
            raise ValueError("Shape mismatch: pred and gt must have the same shape.")

        im_sum = pred.sum() + gt.sum()
        if im_sum == 0:
            return empty_score

        # Compute Dice coefficient
        intersection = np.logical_and(pred, gt)

        return 2. * intersection.sum() / im_sum

    def start(self, ds, **kwargs):
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
                gt_file = join(run_dir, "nnunet-cohort", basename(single_model_pred_file).replace(".nii.gz", ""), self.gt_dir, basename(single_model_pred_file))
                ensemble_file = None
                if self.ensemble_dir != None:
                    ensemble_file = join(self.ensemble_dir, basename(single_model_pred_file))

                if not exists(gt_file):
                    print("# Could not find gt-file !")
                    print(f"# gt:   {gt_file}")
                    exit(1)

                if ensemble_file != None and not exists(ensemble_file):
                    print("# Could not find ensemble_file !")
                    print(f"# ensemble_file:   {ensemble_file}")
                    exit(1)

                # dice_gt_single_model = self.calc_dice(pred=single_model_pred_file, gt=gt_file)
                # print(f"dice_gt_single_model: {dice_gt_single_model}")
                if ensemble_file != None:
                    dice_gt_ensemble = self.calc_dice(pred=ensemble_file, gt=gt_file)
                    print(f"dice_gt_ensemble: {dice_gt_ensemble}")
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
                 ensemble_operator=None,
                 batch_name=None,
                 workflow_dir=None,
                 *args,
                 **kwargs):

        self.gt_dir = gt_operator.operator_out_dir
        self.ensemble_dir = ensemble_operator.operator_out_dir if ensemble_operator != None else None

        super().__init__(
            dag,
            name="dice-eval",
            python_callable=self.start,
            batch_name=batch_name,
            workflow_dir=workflow_dir,
            execution_timeout=timedelta(minutes=20),
            *args,
            **kwargs
        )
