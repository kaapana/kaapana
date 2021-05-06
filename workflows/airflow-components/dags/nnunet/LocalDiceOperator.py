import os
import json
from datetime import timedelta
from multiprocessing.pool import ThreadPool
from glob import glob
from os.path import join, basename, dirname, exists
from pathlib import Path
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import nibabel as nib
import torch
from monai.metrics import compute_meandice
from pprint import pprint
from matplotlib import rcParams
rcParams.update({'figure.autolayout': True})
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


# class LocalDiceOperator():
class LocalDiceOperator(KaapanaPythonBaseOperator):

    def create_plots(self, data_table, table_name, result_dir):
        print(f"# Creating boxplots: {table_name}")
        os.makedirs(result_dir, exist_ok=True)

        plot_labels = sorted(list(data_table.Model.unique()))
        if "ensemble" in plot_labels:
            plot_labels.append(plot_labels.pop(plot_labels.index('ensemble')))

        fig, ax1 = plt.subplots(1, 1, figsize=(12, 14))
        box_plot = sns.boxplot(x="Model", y="Dice", hue="Label", palette="Set3", data=data_table, ax=ax1, order=plot_labels)
        box_plot.set_xticklabels(box_plot.get_xticklabels(), rotation=40, ha="right")

        box = box_plot.get_position()
        box_plot.set_position([box.x0, box.y0, box.width * 0.85, box.height])  # resize position
        box_plot.legend(loc='center right', bbox_to_anchor=(1.22, 0.5), ncol=1)
        plt.tight_layout()
        fig.savefig(join(result_dir, f"pdf_results_{table_name}.pdf"))
        fig.savefig(join(result_dir, f"png_results_{table_name}.png"), dpi=fig.dpi)
        # plt.show()
        print("# DONE")

    def get_model_infos(self, model_batch_dir):
        model_batch_dir = join(model_batch_dir, "model-exports")
        print(f"# Searching for dataset.json @: {model_batch_dir}")
        labels = None
        model_id = None
        model_info = glob(join(model_batch_dir, "**", "dataset.json"), recursive=True)
        if len(model_info) == 0:
            print("# Could not find any dataset.json !")
        elif len(model_info) > 1:
            print("# Found multiple dataset.json !")
        else:
            assert len(model_info) == 1
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

    @staticmethod
    def get_one_hot(targets, nb_classes):
        res = np.eye(nb_classes)[np.array(targets).reshape(-1)]
        return res.reshape(list(targets.shape)+[nb_classes])

    def start(self, ds, **kwargs):
        print("# Evaluating predictions started ...")
        print(f"# workflow_dir {self.workflow_dir}")
        print(f"# operator_in_dir {self.operator_in_dir}")
        print(f"# gt_dir {self. gt_dir}")
        self.anonymize_lookup_table = {}
        case_counter = 0

        result_scores_case_based = {}
        result_scores_model_based = {}
        result_table = []

        # run_dir = self.workflow_dir
        run_dir = os.path.join(self.workflow_dir, kwargs['dag_run'].run_id)
        processed_count = 0

        batch_folders = [f for f in glob(os.path.join(run_dir, self.batch_name, '*'))]
        print("# Found {} batches".format(len(batch_folders)))
        dice_results = {}
        for batch_element_dir in batch_folders:
            print("#")
            print("##################################################")
            print("#")
            print(f"# Processing batch-element: {batch_element_dir}")
            print("#")
            print("##################################################")
            print("#")
            single_model_pred_dir = join(batch_element_dir, "single-model-prediction")
            # single_model_pred_dir = join(batch_element_dir, self.operator_in_dir)
            single_model_pred_files = sorted(glob(join(single_model_pred_dir, "*.nii*"), recursive=False))
            for single_model_pred_file in single_model_pred_files:
                print("#")
                print("##################################################")
                print("#")
                print("# single_model_pred_file:")
                print(f"# {single_model_pred_file}")
                print("#")
                print("##################################################")
                print("#")
                case_counter += 1
                file_id = basename(single_model_pred_file).replace(".nii.gz", "")
                # info_json = single_model_pred_file.replace("nii.gz", "json")
                # with open(info_json) as f:
                #     seg_info = json.load(f)

                gt_dir = join(batch_element_dir, self.gt_dir, "*.nii.gz")
                gt_files = glob(gt_dir, recursive=False)
                print(f"# Found {len(gt_files)} gt-files @ {gt_dir}!")
                assert len(gt_files) != 0

                single_model_prediction = nib.load(single_model_pred_file).get_fdata().astype(int)
                max_label = single_model_prediction.max()
                ground_trouth = nib.load(gt_files[0]).get_fdata().astype(int)
                max_label_gt = ground_trouth.max()
                max_label = max_label_gt if max_label_gt > max_label else max_label

                # nifti_int_encodings.extend(gt_int_encodings)

                one_hot_encoding_pred = (np.arange(max_label+1) == single_model_prediction[..., None]).astype(int).transpose()
                one_hot_encoding_pred = np.expand_dims(one_hot_encoding_pred, axis=0)
                single_model_prediction = None
                one_hot_encoding_gt = (np.arange(max_label+1) == ground_trouth[..., None]).astype(int).transpose()
                one_hot_encoding_gt = np.expand_dims(one_hot_encoding_gt, axis=0)
                ground_trouth = None

                # stack_gt = np.stack(one_hot_encoding_gt,axis=0)
                pred_tensor = torch.from_numpy(one_hot_encoding_pred)
                one_hot_encoding_pred =None

                gt_tensor = torch.from_numpy(one_hot_encoding_gt)
                one_hot_encoding_gt =None

                dice_scores = compute_meandice(y_pred=pred_tensor, y=gt_tensor, include_background=True).numpy()
                
                print("Single prediction:")
                print(dice_scores)
                processed_count+=1
                dice_results[processed_count] = dice_scores
                
                single_model_prediction=None
                ground_trouth=None
                one_hot_encoding_pred=None
                one_hot_encoding_gt=None
                pred_tensor=None
                gt_tensor=None
            
                # if self.ensemble_dir is not None:
                #     en_dir = join(batch_element_dir, self.ensemble_dir, "*.nii.gz")
                #     ensemble_files = glob(en_dir, recursive=False)
                #     print(f"# Found {len(ensemble_files)} ensemble-files @ {en_dir}!")
                #     for en in ensemble_files:
                #         print(en)
                #     assert len(ensemble_files) == 1
                #     ensemble_prediction = nib.load(ensemble_files[0]).get_fdata().astype(int)
                #     one_hot_encoding_en = (np.arange(max_label+1) == ensemble_prediction[..., None]).astype(int).transpose()
                #     ensemble_prediction=None
                #     one_hot_encoding_en = np.expand_dims(one_hot_encoding_en, axis=0)
                #     ensemble_pred_tensor = torch.from_numpy(one_hot_encoding_en)
                #     one_hot_encoding_en=None
                #     dice_scores = compute_meandice(y_pred=ensemble_pred_tensor, y=gt_tensor, include_background=True).numpy()
                #     print("Ensembel:")
                #     print(dice_scores)
                #     dice_results[basename(ensemble_files[0])] = dice_scores
        print("# dice_results: ")
        print("# ")
        print(json.dumps(dice_results, indent=4, sort_keys=True, default=str))
        print("# ")
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
            print("#")
            print(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
            print("#")
            print("# DONE #")


    # def __init__(self):
    #     self.workflow_dir = "/home/jonas/Downloads/dice_test_data/nnunet-ensemble-210505182552676296"
    #     self.batch_name = "nnunet-cohort"

    #     self.gt_dir = "seg-check-gt"
    #     self.ensemble_dir = "ensemble-prediction"
    #     self.operator_in_dir = "single-model-prediction"
    #     self.operator_out_dir = "evaluation"
    #     self.anonymize = True

    def __init__(self,
                 dag,
                 gt_operator,
                 ensemble_operator=None,
                 batch_name=None,
                 workflow_dir=None,
                 anonymize=True,
                 *args,
                 **kwargs):

        self.gt_dir = gt_operator.operator_out_dir
        self.ensemble_dir = ensemble_operator.operator_out_dir if ensemble_operator != None else None
        self.anonymize = anonymize

        super().__init__(
            dag,
            name="dice-eval",
            python_callable=self.start,
            batch_name=batch_name,
            workflow_dir=workflow_dir,
            execution_timeout=timedelta(hours=5),
            *args,
            **kwargs
        )


