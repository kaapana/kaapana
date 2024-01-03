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


# TODO: use merge masks operator to combine i.e. multiple lung masks into "lung"
# TODO: add manual evaluation option, if selected put all data into minio and start jupyterlab


default_interpolation_order = "default"
default_prep_thread_count = 1
default_nifti_thread_count = 1
test_dataset_limit = None
organ_filter = None
seg_filter_gt = ""
seg_filter_test = ""

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
                        "dice-score",
                        "average-surface-distance",
                        "hausdorff-distance",
                    ],
                },
            },
            "test_tag": {
                "title": "Tag for defining test segmentations",
                "description": "The tag must exist in all test segmentations, and must not exist in ground truth data",
                "type": "string",
                "default": "test",
            },
            "seg_filter_test": {
                "title": "Test segmentation filter (optional)",
                "default": seg_filter_test,
                "description": "Select organ for multi-label DICOM SEGs in test samples",
                "type": "string",
                "readOnly": False,
            },
            "seg_filter_gt": {
                "title": "Ground truth segmentation filter (optional)",
                "default": seg_filter_gt,
                "description": "Select organ for multi-label DICOM SEGs in ground truth",
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
    seg_filter=seg_filter_gt,
    batch_name="gt-dataset",
    parallel_id="gt",
)

dcm2nifti_test = Mask2nifitiOperator(
    dag=dag,
    input_operator=get_test_images,
    batch_name="test-dataset",
    seg_filter=seg_filter_test,
    parallel_id="test",
)

evaluation = SegmentationEvaluationOperator(
    dag=dag,
    gt_operator=dcm2nifti_gt,
    test_operator=dcm2nifti_test,
    batch_gt="gt-dataset",
    batch_test="test-dataset",
)

put_to_minio = LocalMinioOperator(
    dag=dag,
    name="upload-evaluation-results",
    zip_files=True,
    action="put",
    action_operators=[evaluation],
    file_white_tuples=(".zip"),
)


clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_gt_images >> dcm2nifti_gt >> evaluation

get_test_images >> get_ref_ct_from_test >> dcm2nifti_test >> evaluation
get_ref_ct_from_test >> dcmconverter_test >> evaluation

evaluation >> put_to_minio >> clean
