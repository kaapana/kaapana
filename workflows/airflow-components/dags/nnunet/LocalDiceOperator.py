import os
import json
import numpy as np
import nibabel as nib
from datetime import timedelta
from multiprocessing.pool import ThreadPool
from glob import glob
from os.path import join, basename, dirname, exists
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalDiceOperator(KaapanaPythonBaseOperator):
    def get_model_infos(self, model_batch_dir):
        model_batch_dir = join(model_batch_dir, "model-exports")
        print(f"# Searching for dataset.json @: {model_batch_dir}")
        labels = None
        model_id = None
        model_info = glob(join(model_batch_dir, "**", "dataset.json"), recursive=True)
        if len(model_info) == 0:
            print("# Could not find any dataset.json !")
        if len(model_info) > 1:
            print("# Found multiple dataset.json !")
            assert len(model_info) == 1

        else:
            with open(model_info[0]) as f:
                dataset_json = json.load(f)
            labels = dataset_json["labels"]
            model_id = dataset_json["name"]

        return labels, model_id

    def prep_nifti(self, nifti_path):
        nifti_numpy = nib.load(nifti_path).get_fdata().astype(int)
        nifti_labels = list(np.unique(nifti_numpy))

        if 0 in nifti_labels:
            nifti_labels.remove(0)
        else:
            print("#")
            print(f"# Couldn't find a 'Clear Label' 0 in NIFTI!")
            print(f"# NIFTI-path: {nifti_path}")
            print("#")
            exit(1)

        return nifti_numpy, nifti_labels

    def calc_dice(self, pred, gt, empty_score=1.0):
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
        model_count = 0

        result_scores_sm = {}
        result_scores_ensemble = {}

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
            model_count += 1
            labels, model_id = self.get_model_infos(model_batch_dir=batch_element_dir)
            model_id = f"{model_id}_{model_count}"
            result_scores_sm[model_id] = {}
            print(f"# processing batch-element: {batch_element_dir}")
            single_model_pred_dir = join(batch_element_dir, self.operator_in_dir)
            single_model_pred_files = sorted(glob(join(single_model_pred_dir, "*.nii*"), recursive=False))
            for single_model_pred_file in single_model_pred_files:
                processed_count += 1
                file_id = basename(single_model_pred_file).replace(".nii.gz", "")
                gt_file = join(run_dir, "nnunet-cohort", file_id, self.gt_dir, basename(single_model_pred_file))
                result_scores_sm[model_id][file_id] = {}

                if not exists(gt_file):
                    print("# Could not find gt-file !")
                    print(f"# gt:   {gt_file}")
                    exit(1)
                result_scores_sm[model_id][file_id]["gt_file"] = gt_file
                result_scores_sm[model_id][file_id]["pred_file"] = single_model_pred_file
                gt_numpy, gt_labels = self.prep_nifti(gt_file)
                sm_numpy, sm_labels = self.prep_nifti(single_model_pred_file)

                result_scores_sm[model_id][file_id]["label_predictions"] = {}
                for pred_label in sm_labels:
                    label_key = labels[str(pred_label)] if labels != None and str(pred_label) in labels else None
                    if label_key == None and labels != None:
                        print("##################################################")
                        print("#")
                        print("##################### INFO ######################")
                        print("#")
                        print(f"# predicted label {pred_label}: {label_key} can't be found in gt!")
                        print(f"# pred_label in gt_labels: {pred_label in gt_labels}")
                        print("#")
                        print("##################################################")
                        # assert pred_label in gt_labels
                    else:
                        result_scores_sm[model_id][file_id]["label_predictions"][str(pred_label)]={}
                        label_strip_gt = (gt_numpy == pred_label).astype(int)
                        label_strip_sm = (sm_numpy == pred_label).astype(int)
                        dice_result = self.calc_dice(pred=label_strip_sm, gt=label_strip_gt)
                        print("#")
                        print(f"# Single Model evalualtion: {model_id}")
                        print(f"Label: {pred_label} -> {label_key}")
                        print(f"Dice:  {dice_result}")
                        print("#")
                        result_scores_sm[model_id][file_id]["label_predictions"][str(pred_label)]["label_id"] = pred_label
                        result_scores_sm[model_id][file_id]["label_predictions"][str(pred_label)]["label_name"] = label_key
                        result_scores_sm[model_id][file_id]["label_predictions"][str(pred_label)]["dice"] = dice_result

                ensemble_numyp = None
                ensemble_labels = None
                if self.ensemble_dir != None and file_id not in result_scores_ensemble:
                    result_scores_ensemble[file_id] = {}
                    ensemble_file = join(self.ensemble_dir, basename(single_model_pred_file))
                    ensemble_numyp, ensemble_labels = self.prep_nifti(ensemble_file)

                    result_scores_ensemble[file_id]["ensemble_file"] = ensemble_file
                    result_scores_ensemble[file_id]["gt_file"] = gt_file
                    result_scores_ensemble[file_id]["label_predictions"] = {}
                    for pred_label in ensemble_labels:
                        label_key = labels[str(pred_label)] if str(pred_label) in labels else str(pred_label)
                        if label_key == None and labels != None:
                            print("##################################################")
                            print("#")
                            print("##################### INFO ######################")
                            print("#")
                            print(f"# predicted label {pred_label}: {label_key} can't be found in gt!")
                            print(f"# pred_label in gt_labels: {pred_label in gt_labels}")
                            print("#")
                            print("##################################################")
                            # assert pred_label in gt_labels
                        else:
                            result_scores_ensemble[file_id]["label_predictions"][str(pred_label)]={}
                            label_strip_gt = (gt_numpy == pred_label).astype(int)
                            label_strip_ensemble = (ensemble_numyp == pred_label).astype(int)
                            dice_result = self.calc_dice(pred=label_strip_ensemble, gt=label_strip_gt)
                            print("#")
                            print(f"# Ensemble evalualtion: {model_id}")
                            print(f"Label: {pred_label} -> {label_key}")
                            print(f"Dice:  {dice_result}")
                            print("#")
                            result_scores_ensemble[file_id]["label_predictions"][str(pred_label)]["label_id"] = pred_label
                            result_scores_ensemble[file_id]["label_predictions"][str(pred_label)]["label_name"] = label_key
                            result_scores_ensemble[file_id]["label_predictions"][str(pred_label)]["dice"] = dice_result

                print("##################################################")

        print("# ")
        print("# RESULTS: ")
        print("# ")
        print("# SINGLE MODEL")
        print(result_scores_sm)
        print(f"# type(result_scores_sm): {type(result_scores_sm)}")
        print(json.dumps(result_scores_sm, indent=4, sort_keys=True, default=str))
        print("# ")
        print("# ENSEMBLE")
        print(json.dumps(result_scores_ensemble, indent=4, sort_keys=True, default=str))
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
