from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator
from kaapana.operators.Mask2nifitiOperator import Mask2nifitiOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.SegmentationEvaluationOperator import (
    SegmentationEvaluationOperator,
)
from kaapana.operators.MergeMasksOperator import MergeMasksOperator
from kaapana.operators.LocalFilterMasksOperator import LocalFilterMasksOperator


# TODO: add manual evaluation option, if selected put all data into minio and start jupyterlab

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
            "metrics": {
                "title": "Evaluation metrics available",
                "description": "Select segmentation metrics",
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "dice_score",
                        "surface_dice",
                        "average_surface_distance",
                        "hausdorff_distance",
                    ],
                },
            },
            "test_tag": {
                "title": "Tag for defining test segmentations",
                "description": "The tag must exist in all test segmentations, and must not exist in ground truth data",
                "type": "string",
                "default": "test",
            },
            "gt_label_filter": {
                "title": "Filter Ground Truth Seg Masks with keyword 'Ignore' or 'Keep'",
                "default": "",
                "description": "'Ignore' or 'Keep' labels of multi-label DICOM SEGs for segmentation task: e.g. 'Keep: liver' or 'Ignore: spleen,liver'",
                "type": "string",
                "readOnly": False,
            },
            "test_label_filter": {
                "title": "Filter Test Seg Masks with keyword 'Ignore' or 'Keep'",
                "default": "",
                "description": "'Ignore' or 'Keep' labels of multi-label DICOM SEGs for segmentation task: e.g. 'Keep: liver' or 'Ignore: spleen,liver'",
                "type": "string",
                "readOnly": False,
            },
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
            "test_fuse_labels": {
                "title": "Test Fuse Segmentation Labels",
                "description": "Segmentation label maps which should be fused (all special characters are removed).",
                "type": "string",
                "readOnly": False,
            },
            "test_fused_label_name": {
                "title": "Test Fuse Segmentation Label: New Label Name",
                "description": "Segmentation label name of segmentation label maps which should be fused (all special characters are removed).",
                "type": "string",
                "readOnly": False,
            },
            "label_mapping": {
                "title": "Label Mappings",
                "description": "Label mapping after filter and fusing, in the format of 'gt_label_x:test_label_y,gt_label_z:test_label_t'. Only labels included here will be evaluated",
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
    dag_id="evaluate-segmentations",
    default_args=args,
    concurrency=3,
    max_active_runs=2,
    schedule_interval=None,
)

get_gt_images = LocalGetInputDataOperator(
    dag=dag,
    name="get-gt-images",
    batch_name="gt-dataset",
    dataset_limit=None,
    parallel_downloads=5,
    check_modality=False,
    exclude_custom_tag_property="test_tag",
)

get_test_images = LocalGetInputDataOperator(
    dag=dag,
    name="get-test-images",
    batch_name="test-dataset",
    dataset_limit=None,
    parallel_downloads=5,
    check_modality=False,
    include_custom_tag_property="test_tag",
)

get_ref_ct_from_test = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_test_images,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="test",
    modality=None,
    batch_name="test-dataset",
)

dcmconverter_test = DcmConverterOperator(
    dag=dag,
    input_operator=get_ref_ct_from_test,
    parallel_id="test",
    parallel_processes=parallel_processes,
    batch_name="test-dataset",
    output_format="nii.gz",
)

dcm2nifti_gt = Mask2nifitiOperator(
    dag=dag,
    input_operator=get_gt_images,
    batch_name="gt-dataset",
    parallel_id="gt",
)

filter_gt = LocalFilterMasksOperator(
    dag=dag,
    name="filter-masks",
    label_filter_key="gt_label_filter",
    input_operator=dcm2nifti_gt,
    batch_name="gt-dataset",
)

fuse_gt = MergeMasksOperator(
    dag=dag,
    name="fuse-masks-gt",
    input_operator=filter_gt,
    batch_name="gt-dataset",
    mode="fuse",
    fuse_labels_key="gt_fuse_labels",
    fused_label_name_key="gt_fused_label_name",
)

dcm2nifti_test = Mask2nifitiOperator(
    dag=dag,
    input_operator=get_test_images,
    batch_name="test-dataset",
    parallel_id="test",
)

filter_test = LocalFilterMasksOperator(
    dag=dag,
    name="filter-masks",
    label_filter_key="test_label_filter",
    input_operator=dcm2nifti_test,
    batch_name="test-dataset",
)

fuse_test = MergeMasksOperator(
    dag=dag,
    name="fuse-masks-test",
    batch_name="test-dataset",
    input_operator=filter_test,
    mode="fuse",
    fuse_labels_key="test_fuse_labels",
    fused_label_name_key="test_fused_label_name",
)

evaluation = SegmentationEvaluationOperator(
    dag=dag,
    gt_operator=fuse_gt,
    test_operator=fuse_test,
    batch_gt="gt-dataset",
    batch_test="test-dataset",
    metrics_key="metrics",
    trigger_rule="none_failed",
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

get_gt_images >> dcm2nifti_gt >> filter_gt >> fuse_gt >> evaluation

(
    get_test_images
    >> get_ref_ct_from_test
    >> dcm2nifti_test
    >> filter_test
    >> fuse_test
    >> evaluation
)
get_ref_ct_from_test >> dcmconverter_test >> evaluation

evaluation >> put_to_minio >> clean
