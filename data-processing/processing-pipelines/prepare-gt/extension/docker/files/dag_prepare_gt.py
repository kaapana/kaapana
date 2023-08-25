from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.Mask2nifitiOperator import Mask2nifitiOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from prepare_gt.LocalSortGtToRefOperator import LocalSortGtToRefOperator
from prepare_gt.LocalGetMasterLabelListOperator import LocalGetMasterLabelListOperator
from prepare_gt.MergeNiftisOperator import MergeNiftisOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator

log = LoggingMixin().log
ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "seg_filter": {
                "title": "Segmentation Mask Filter",
                "default": "",
                "required": True,
                "description": "Add labels to be kept - this list is case-insensitive!",
                "type": "array",
                "items": {
                    "type": "string",
                },
                "readOnly": False,
            },
            "merge_segs_config": {
                "title": "Configure Label Merge",
                "default": "",
                "description": "Optional possibility to merge or rename labels.",
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["merge_labels", "target_label"],
                    "properties": {
                        "merge_labels": {
                            "type": "array",
                            "title": "Labels to be merged or renamed",
                            "items": {
                                "type": "string",
                            },
                        },
                        "target_label": {"type": "string", "title": "Target Label"},
                    },
                },
                "readOnly": False,
            },
            "input": {
                "title": "Input Modality",
                "default": "SEG,RTSTRUCT",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
                "required": True,
            },
            "overlap_strategy": {
                "title": "resolve overlap strategy",
                "default": "crash",
                "description": "Set overlap strategy",
                "enum": [
                    "none",
                    "skip",
                    "crash",
                    "set_to_background",
                    "follow_label_list",
                ],
                "type": "string",
                "readOnly": False,
                "required": True,
            },
            "overlap_threshold": {
                "title": "Threshold for the overlap detection (%)",
                "default": 0.01,
                "description": "Maximum percentage of allowed overlap voxels",
                "type": "number",
                "readOnly": False,
                "required": True,
            },
            "single_execution": {
                "type": "boolean",
                "title": "Single execution",
                "description": "Whether your report is execute in single mode or not",
                "default": False,
                "readOnly": True,
            },
        },
    },
}

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="prepare-gt",
    default_args=args,
    concurrency=2,
    max_active_runs=1,
    schedule_interval=None,
)

get_input = LocalGetInputDataOperator(
    dag=dag, check_modality=True, parallel_downloads=5
)


get_ref_ct_series_from_seg = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_input,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
    modality=None,
)

sort_gt_to_ref = LocalSortGtToRefOperator(
    dag=dag,
    base_dcm_operator=get_ref_ct_series_from_seg,
    gt_dcm_operator=get_input,
    new_batch_name="sorted",
    move_files=True,
)

dcm2nifti_seg = Mask2nifitiOperator(
    dag=dag,
    input_operator=get_input,
    dicom_operator=get_ref_ct_series_from_seg,
    seg_filter="",
    batch_name="sorted",
)

dcm2nifti_ct = DcmConverterOperator(
    dag=dag,
    input_operator=get_ref_ct_series_from_seg,
    output_format="nii.gz",
    batch_name="sorted",
)


master_label_list = LocalGetMasterLabelListOperator(
    dag=dag, batch_name="sorted", input_operator=dcm2nifti_seg
)

merge_masks = MergeNiftisOperator(
    dag=dag, batch_name="sorted", input_operator=dcm2nifti_seg
)

nrrd2dcmSeg_multi = Itk2DcmSegOperator(
    dag=dag,
    input_operator=get_ref_ct_series_from_seg,
    segmentation_operator=merge_masks,
    batch_name="sorted",
    input_type="multi_label_seg",
    skip_empty_slices=True,
    fail_on_no_segmentation_found=False,
)

dcmseg_send_multi = DcmSendOperator(
    dag=dag, batch_name="sorted", input_operator=nrrd2dcmSeg_multi
)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=False)

(
    get_input
    >> get_ref_ct_series_from_seg
    >> sort_gt_to_ref
    >> dcm2nifti_ct
    >> merge_masks
    >> nrrd2dcmSeg_multi
    >> dcmseg_send_multi
    >> clean
)
sort_gt_to_ref >> dcm2nifti_seg >> master_label_list >> merge_masks
