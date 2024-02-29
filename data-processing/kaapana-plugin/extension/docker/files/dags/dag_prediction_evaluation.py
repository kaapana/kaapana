from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG

from kaapana.operators.GetZenodoModelOperator import GetZenodoModelOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.Mask2nifitiOperator import Mask2nifitiOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator

# from kaapana.operators.SegmentationEvaluationOperator import (
#     SegmentationEvaluationOperator,
# )
from kaapana.operators.LocalFilterMasksOperator import LocalFilterMasksOperator
from kaapana.operators.LocalModifySegLabelNamesOperator import (
    LocalModifySegLabelNamesOperator,
)
from totalsegmentator.TotalSegmentatorOperator import TotalSegmentatorOperator
from nnunet.DiceEvaluationOperator import DiceEvaluationOperator
from nnunet.SegCheckOperator import SegCheckOperator
from kaapana.operators.MergeMasksOperator import MergeMasksOperator

from kaapana.operators.LocalFormatForSegCheckOperator import (
    LocalFormatForSegCheckOperator,
)

# NOTE: this is an experimental DAG designed for evaluation with running nnunet-predict with only providing the ground truth segmentations
# NOTE: this DAG will only run if nnunet is installed
# NOTE: for a stable evaluation DAG where it is possible to compare test and ground truth segmentations, please refer to dag_segmentation_evaluation.py

default_interpolation_order = "default"
default_prep_thread_count = 1
default_nifti_thread_count = 1
test_dataset_limit = None
organ_filter = None

parallel_processes = 3
ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            # filter labels
            "gt_label_filter": {
                "title": "Filter Ground Truth Seg Masks with keyword 'Ignore' or 'Keep'",
                "default": "",
                "description": "'Ignore' or 'Keep' labels of multi-label DICOM SEGs for segmentation task: e.g. 'Keep: liver' or 'Ignore: spleen,liver'",
                "type": "string",
                "readOnly": False,
            },
            "pred_label_filter": {
                "title": "Filter Prediction Seg Masks with keyword 'Ignore' or 'Keep'",
                "default": "",
                "description": "'Ignore' or 'Keep' labels of multi-label DICOM SEGs for segmentation task: e.g. 'Keep: liver' or 'Ignore: spleen,liver'",
                "type": "string",
                "readOnly": False,
            },
            # fuse labels
            "gt_fuse_labels": {
                "title": "Ground Truth Fuse Segmentation Labels",
                "description": "Segmentation label maps which should be fused (all special characters are removed).",
                "type": "string",
                "readOnly": False,
            },
            "gt_fused_label_name": {
                "title": "Ground Truth Fuse Segmentation Label: New Label Name",
                "description": "Segmentation label name of segmentation label maps which should be fused (all special characters are removed).",
                "type": "string",
                "readOnly": False,
            },
            # "pred_fuse_labels": {
            #     "title": "Pred Fuse Segmentation Labels",
            #     "description": "Segmentation label maps which should be fused (all special characters are removed).",
            #     "type": "string",
            #     "readOnly": False,
            # },
            # "pred_fused_label_name": {
            #     "title": "Pred Fuse Segmentation Label: New Label Name",
            #     "description": "Segmentation label name of segmentation label maps which should be fused (all special characters are removed).",
            #     "type": "string",
            #     "readOnly": False,
            # },
            # rename labels
            "old_labels": {
                "title": "Rename Label Names: Old Labels",
                "description": "Old segmentation label names which should be overwritten (all special characters are removed); SAME ORDER AS NEW LABEL NAMES REQUIRED!!!",
                "type": "string",
                "readOnly": False,
            },
            "new_labels": {
                "title": "Rename Label Names: New Labels",
                "description": "New segmentation label names which should overwrite the old segmentation label names (all special characters are removed); SAME ORDER AS OLD LABEL NAMES REQUIRED!!!",
                "type": "string",
                "readOnly": False,
            },
            # total segmentator
            "fast": {
                "title": "--fast",
                "description": "Run faster lower resolution model.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "preview": {
                "title": "--preview",
                "description": "Generate a png preview for the segmentation.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "statistics": {
                "title": "--statistics",
                "description": "Calc volume (in mm3) and mean intensity. Results will be in statistics.json.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "radiomics": {
                "title": "--radiomics",
                "description": "Calc radiomics features. Requires pyradiomics. Results will be in statistics_radiomics.json.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "verbose": {
                "title": "--verbose",
                "description": "Show more intermediate output.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "quiet": {
                "title": "--quiet",
                "description": "Print no intermediate outputs.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "forcesplit": {
                "title": "--force_split",
                "description": "Process image in 3 chunks for less memory consumption.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "bodyseg": {
                "title": "--body_seg",
                "description": "Do initial rough body segmentation and crop image to body region.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "lung_vessels": {
                "title": "enable lung_vessels",
                "description": "Add segmentations for lung_vessels and lung_trachea_bronchia.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "cerebral_bleed": {
                "title": "enable cerebral_bleed",
                "description": "Add segmentations for intracerebral_hemorrhage.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "hip_implant": {
                "title": "enable hip_implant",
                "description": "Add segmentations for hip_implant.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "coronary_arteries": {
                "title": "enable coronary_arteries",
                "description": "Add segmentations for coronary_arteries.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "body": {
                "title": "enable body",
                "description": "Add segmentations for body, body_trunc, body_extremities, skin",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "pleural_pericard_effusion": {
                "title": "enable pleural_pericard_effusion",
                "description": "Add segmentations for pleural_effusion and pericardial_effusion.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "nr_thr_resamp": {
                "title": "resampling thread count",
                "description": "Nr of threads for resampling.",
                "default": 1,
                "type": "integer",
                "readOnly": False,
                "required": True,
            },
            "nr_thr_saving": {
                "title": "saving thread count",
                "description": "Nr of threads for saving segmentations.",
                "default": 6,
                "type": "integer",
                "readOnly": False,
                "required": True,
            },
            # data
            "input": {
                "title": "Input Modality",
                "default": "SEG",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
            },
            # single execution
            "single_execution": {
                "type": "boolean",
                "title": "Single execution",
                "description": "Whether your report is execute in single mode or not",
                "default": False,
                "readOnly": True,
            },
        },
    }
}

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=60),
}

dag = DAG(
    dag_id="evaluate-predictions",
    default_args=args,
    concurrency=3,
    max_active_runs=2,
    schedule_interval=None,
)

get_gt_seg = LocalGetInputDataOperator(
    dag=dag,
    name="get-gt-seg",
    dataset_limit=None,
    parallel_downloads=5,
    check_modality=False,
)

get_ref_ct = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_gt_seg,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
    modality=None,
)

dcm2nifti_ct = DcmConverterOperator(
    dag=dag,
    input_operator=get_ref_ct,
    parallel_id="ct",
    parallel_processes=parallel_processes,
    output_format="nii.gz",
)

ta = "total"
get_total_segmentator_model_0 = GetZenodoModelOperator(
    dag=dag,
    model_dir="/models/total_segmentator/nnUNet",
    task_ids="Task251_TotalSegmentator_part1_organs_1139subj,Task252_TotalSegmentator_part2_vertebrae_1139subj,Task253_TotalSegmentator_part3_cardiac_1139subj,Task254_TotalSegmentator_part4_muscles_1139subj,Task255_TotalSegmentator_part5_ribs_1139subj,Task256_TotalSegmentator_3mm_1139subj",
)
total_segmentator_0 = TotalSegmentatorOperator(
    dag=dag, input_operator=dcm2nifti_ct, task=ta
)

ta = "pleural_pericard_effusion"
get_total_segmentator_model_6 = GetZenodoModelOperator(
    dag=dag,
    model_dir="/models/total_segmentator/nnUNet",
    task_ids="Task315_thoraxCT",
    parallel_id=ta,
)
total_segmentator_6 = TotalSegmentatorOperator(
    dag=dag,
    task=ta,
    input_operator=dcm2nifti_ct,
    delete_output_on_start=False,
    parallel_id=ta,
)

filter_pred = LocalFilterMasksOperator(
    dag=dag,
    name="filter-masks-pred",
    label_filter_key="pred_label_filter",
    input_operator=total_segmentator_6,
)

# fuse_pred = MergeMasksOperator(
#     dag=dag,
#     name="fuse-masks-pred",
#     input_operator=filter_pred,
#     mode="fuse",
#     fuse_labels_key="test_fuse_labels",
#     fused_label_name_key="test_fused_label_name",
# )

rename_pred = LocalModifySegLabelNamesOperator(
    dag=dag,
    input_operator=filter_pred,
    metainfo_input_operator=filter_pred,
    results_to_in_dir=False,
    write_seginfo_results=True,
    write_metainfo_results=False,
    trigger_rule="all_done",
)

format_for_segcheck_pred = LocalFormatForSegCheckOperator(
    dag=dag,
    input_operator=rename_pred,
)

seg_check_pred = SegCheckOperator(
    dag=dag,
    input_operator=format_for_segcheck_pred,
    original_img_operator=dcm2nifti_ct,
    target_dict_operator=None,
    parallel_processes=parallel_processes,
    max_overlap_percentage=100,
    merge_found_niftis=False,
    delete_merged_data=False,
    fail_if_overlap=False,
    fail_if_label_already_present=False,
    fail_if_label_id_not_extractable=False,
    force_same_labels=False,
    parallel_id="pred",
    # dev_server="code-server"
)

mask2nifti_gt = Mask2nifitiOperator(
    dag=dag,
    input_operator=get_gt_seg,
    parallel_id="gt",
)

filter_gt = LocalFilterMasksOperator(
    dag=dag,
    name="filter-masks",
    label_filter_key="gt_label_filter",
    input_operator=mask2nifti_gt,
)

fuse_gt = MergeMasksOperator(
    dag=dag,
    name="fuse-masks-gt",
    input_operator=filter_gt,
    mode="fuse",
    fuse_labels_key="gt_fuse_labels",
    fused_label_name_key="gt_fused_label_name",
)

rename_gt = LocalModifySegLabelNamesOperator(
    dag=dag,
    input_operator=fuse_gt,
    metainfo_input_operator=fuse_gt,
    results_to_in_dir=False,
    write_seginfo_results=True,
    write_metainfo_results=False,
    trigger_rule="all_done",
)

format_for_segcheck_gt = LocalFormatForSegCheckOperator(
    dag=dag,
    input_operator=rename_gt,
)

seg_check_gt = SegCheckOperator(
    dag=dag,
    input_operator=format_for_segcheck_gt,
    original_img_operator=dcm2nifti_ct,
    target_dict_operator=seg_check_pred,
    parallel_processes=parallel_processes,
    max_overlap_percentage=100,
    merge_found_niftis=True,
    delete_merged_data=False,
    fail_if_overlap=False,
    fail_if_label_already_present=False,
    fail_if_label_id_not_extractable=False,
    force_same_labels=False,
    parallel_id="gt",
    # dev_server="code-server"
)

# evaluation = SegmentationEvaluationOperator(
#     dag=dag,
#     gt_operator=combine_gt,
#     test_operator=combine_pred,
#     batch_gt="nnunet-dataset",
#     batch_test=None,
#     test_seg_exists=False,
#     trigger_rule="none_failed",
#     dev_server="code-server"
# )
evaluation = DiceEvaluationOperator(
    dag=dag,
    anonymize=True,
    gt_operator=seg_check_gt,
    input_operator=seg_check_pred,
    ensemble_operator=get_gt_seg,  # just as a dummy
    parallel_processes=1,
    trigger_rule="all_done",
    # dev_server="code-server"
)

put_to_minio = LocalMinioOperator(
    dag=dag,
    name="put-eval-metrics-to-minio",
    zip_files=True,
    action="put",
    action_operators=[evaluation],
    file_white_tuples=(".zip"),
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)


get_gt_seg >> get_ref_ct >> dcm2nifti_ct >> total_segmentator_0
(
    get_total_segmentator_model_0
    >> total_segmentator_0
    >> get_total_segmentator_model_6
    >> total_segmentator_6
    >> filter_pred
    # >> fuse_pred
    >> rename_pred
    >> format_for_segcheck_pred
    >> seg_check_pred
    >> evaluation
)
(
    get_gt_seg
    >> mask2nifti_gt
    >> filter_gt
    >> fuse_gt
    >> rename_gt
    >> format_for_segcheck_gt
    >> seg_check_gt
    >> evaluation
)
seg_check_pred >> seg_check_gt
evaluation >> put_to_minio >> clean

# get_gt_seg >> get_ref_ct >> dcm2nifti_ct >> total_segmentator_0
# get_total_segmentator_model_0 >> total_segmentator_0 >> get_total_segmentator_model_6 >> total_segmentator_6 >> combine_pred >> evaluation
# get_gt_seg >> mask2nifti_gt >> combine_gt >> evaluation

# evaluation >> put_to_minio >> clean
