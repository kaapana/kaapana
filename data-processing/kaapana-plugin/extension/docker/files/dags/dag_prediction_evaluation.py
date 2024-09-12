from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.GetZenodoModelOperator import GetZenodoModelOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator
from nnunet.LocalModelGetInputDataOperator import LocalModelGetInputDataOperator
from kaapana.operators.Mask2nifitiOperator import Mask2nifitiOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.SegmentationEvaluationOperator import (
    SegmentationEvaluationOperator,
)
from kaapana.operators.MergeMasksOperator import MergeMasksOperator
from kaapana.operators.LocalFilterMasksOperator import LocalFilterMasksOperator
from kaapana.operators.LocalModifySegLabelNamesOperator import (
    LocalModifySegLabelNamesOperator,
)

from nnunet.NnUnetOperator import NnUnetOperator
from nnunet.NnUnetModelOperator import NnUnetModelOperator
from nnunet.getTasks import get_available_protocol_names


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
            "WARNING":  {
                "title": "WARNING: experimental DAG for evaluating nnunet-predict",
                "default": "Use the stable evaluation DAG: evaluate-segmentations",
                "description": "WARNING: this DAG will only run if nnunet is installed",
                "type": "string",
                "readOnly": True,
            },
            "metrics": {
                "title": "Evaluation metrics available",
                "description": "Select segmentation metrics",
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "surface_dice",
                        "average_surface_distance",
                        "hausdorff_distance",
                    ],
                },
            },
            "label_filter": {
                "title": "Filter Seg Masks with keyword 'Ignore' or 'Keep'",
                "default": "",
                "description": "'Ignore' or 'Keep' labels of multi-label DICOM SEGs for segmentation task: e.g. 'Keep: liver' or 'Ignore: spleen,liver'",
                "type": "string",
                "readOnly": False,
            },
            "fuse_labels": {
                "title": "Fuse Segmentation Labels",
                "description": "Segmentation label maps which should be fused (all special characters are removed).",
                "type": "string",
                "readOnly": False,
            },
            "fused_label_name": {
                "title": "Fuse Segmentation Label: New Label Name",
                "description": "Segmentation label name of segmentation label maps which should be fused (all special characters are removed).",
                "type": "string",
                "readOnly": False,
            },
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
            "exit_on_error": {
                "title": "Exit on evaluation error",
                "default": True,
                "description": "Exit if there is an issue with evaluating one of the masks",
                "type": "boolean",
                "readOnly": False,
            },
            "tasks": {
                "title": "Tasks available",
                "description": "Select available tasks",
                "type": "array",
                "items": {"type": "string", "enum": get_available_protocol_names()},
            },
            "model": {
                "title": "Pre-trained models",
                "description": "Select one of the available models.",
                "type": "string",
                "default": "3d_lowres",
                "required": True,
                "enum": ["2d", "3d_fullres", "3d_lowres", "3d_cascade_fullres"],
            },
            "inf_softmax": {
                "title": "enable softmax",
                "description": "Enable softmax export?",
                "type": "boolean",
                "default": True,
                "readOnly": False,
            },
            "interpolation_order": {
                "title": "interpolation order",
                "default": "default",
                "description": "Set interpolation_order.",
                "enum": ["default", "0", "1", "2", "3"],
                "type": "string",
                "readOnly": False,
                "required": True,
            },
            "inf_threads_prep": {
                "title": "Pre-processing threads",
                "type": "integer",
                "default": 1,
                "description": "Set pre-processing thread count.",
                "required": True,
            },
            "inf_threads_nifti": {
                "title": "NIFTI threads",
                "type": "integer",
                "description": "Set NIFTI export thread count.",
                "default": 1,
                "required": True,
            },
            "input": {
                "title": "Input Modality",
                "default": "SEG",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
            },
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
    batch_name="nnunet-dataset"
)

get_ref_ct = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_gt_seg,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="gt",
    modality=None,
    batch_name="nnunet-dataset"
)

dcm2nifti_ct = DcmConverterOperator(
    dag=dag,
    input_operator=get_ref_ct,
    parallel_id="gt",
    parallel_processes=parallel_processes,
    output_format="nii.gz",
    batch_name="nnunet-dataset"
)

get_model = LocalModelGetInputDataOperator(
    dag=dag, name="get-model", check_modality=True, parallel_downloads=5
)

dcm2bin = Bin2DcmOperator(
    dag=dag, input_operator=get_model, name="extract-binary", file_extensions="*.dcm"
)

extract_model = NnUnetModelOperator(
    dag=dag,
    name="unzip-models",
    target_level="batch_element",
    input_operator=dcm2bin,
    operator_out_dir="model-exports",
)

nnunet_predict = NnUnetOperator(
    dag=dag,
    mode="inference",
    input_modality_operators=[dcm2nifti_ct],
    inf_batch_dataset=True,
    inf_remove_if_empty=False,
    models_dir=extract_model.operator_out_dir,
    # dev_server="code-server"
)

mask2nifti_gt = Mask2nifitiOperator(
    dag=dag,
    input_operator=get_gt_seg,
    parallel_id="gt",
    batch_name="nnunet-dataset"
)

filter_gt = LocalFilterMasksOperator(
    dag=dag,
    name="filter-masks",
    label_filter_key="gt_label_filter",
    input_operator=mask2nifti_gt,
    batch_name="nnunet-dataset"
)

fuse_gt = MergeMasksOperator(
    dag=dag,
    name="fuse-masks",
    input_operator=filter_gt,
    mode="fuse",
    trigger_rule="all_done",
    batch_name="nnunet-dataset"
)

rename_gt = LocalModifySegLabelNamesOperator(
    dag=dag,
    input_operator=fuse_gt,
    metainfo_input_operator=fuse_gt,
    results_to_in_dir=False,
    write_seginfo_results=False,
    write_metainfo_results=True,
    trigger_rule="all_done",
    batch_name="nnunet-dataset"
)

combine_gt = MergeMasksOperator(
    dag=dag,
    name="combine-masks-gt",
    input_operator=filter_gt,
    mode="combine",
    batch_name="nnunet-dataset"
)

evaluation = SegmentationEvaluationOperator(
    dag=dag,
    gt_operator=combine_gt,
    test_operator=nnunet_predict,
    batch_gt="nnunet-dataset",
    batch_test=None,
    test_seg_exists=False,
    trigger_rule="none_failed",
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

get_model >> dcm2bin >> extract_model >> nnunet_predict
get_gt_seg >> get_ref_ct >> dcm2nifti_ct >> nnunet_predict
nnunet_predict >> evaluation
get_gt_seg >> mask2nifti_gt >> filter_gt >> fuse_gt >> rename_gt >> combine_gt >> evaluation

evaluation >> put_to_minio >> clean
