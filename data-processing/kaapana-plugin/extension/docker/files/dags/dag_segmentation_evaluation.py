from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from nnunet.DiceEvaluationOperator import DiceEvaluationOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator
from kaapana.operators.Mask2nifitiOperator import Mask2nifitiOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator

from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator
from kaapana.operators.Mask2nifitiOperator import Mask2nifitiOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator

from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from nnunet.SegCheckOperator import SegCheckOperator
from nnunet.NnUnetNotebookOperator import NnUnetNotebookOperator


# TODO: rm nnunet specific operators
# TODO: change to a standalone extension if a separate DiceEvaluation operator is added

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

get_ref_ct_from_gt = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_gt_images,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="gt",
    modality=None,
    batch_name="gt-dataset",
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

dcmconverter_gt = DcmConverterOperator(
    dag=dag,
    input_operator=get_ref_ct_from_gt,
    parallel_id="gt",
    parallel_processes=parallel_processes,
    batch_name="gt-dataset",
    output_format="nii.gz",
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

dcm2nifti_test = Mask2nifitiOperator(
    dag=dag,
    input_operator=get_test_images,
    batch_name="test-dataset",
    parallel_id="test",
)

seg_check_gt = SegCheckOperator(
    dag=dag,
    name="seg_check_gt",
    input_operator=dcm2nifti_gt,
    original_img_operator=dcmconverter_gt,
    target_dict_operator=None, # TODO: check out what this does
    parallel_processes=parallel_processes,
    max_overlap_percentage=100,
    merge_found_niftis=True,
    delete_merged_data=False,
    fail_if_overlap=False,
    fail_if_label_already_present=False,
    fail_if_label_id_not_extractable=False,
    force_same_labels=False,
    batch_name="gt-dataset",
)

seg_check_test = SegCheckOperator(
    dag=dag,
    name="seg_check_test",
    input_operator=dcm2nifti_test,
    original_img_operator=dcmconverter_test,
    parallel_processes=parallel_processes,
    max_overlap_percentage=100,
    merge_found_niftis=False,
    delete_merged_data=False,
    fail_if_overlap=False,
    fail_if_label_already_present=False,
    fail_if_label_id_not_extractable=False,
    force_same_labels=False,
    batch_name="test-dataset",
)

# TODO: Add a new operator that can link segmentantations based on reference CTs with two different batches
evaluation = DiceEvaluationOperator(
    dag=dag,
    dev_server="code-server",
    anonymize=True,
    gt_operator=seg_check_gt,
    input_operator=seg_check_test,
    parallel_processes=1,
    trigger_rule="all_done",
    batch_name=str(get_test_images.operator_out_dir),
)

nnunet_evaluation_notebook = NnUnetNotebookOperator(
    dag=dag,
    name="nnunet-evaluation-notebook",
    input_operator=evaluation,
    arguments=["/kaapana/app/notebooks/evaluation_notebook.sh"],
)

put_to_minio = LocalMinioOperator(
    dag=dag,
    name="upload-nnunet-evaluation",
    zip_files=True,
    action="put",
    action_operators=[evaluation, nnunet_evaluation_notebook],
    file_white_tuples=(".zip"),
)

put_report_to_minio = LocalMinioOperator(
    dag=dag,
    name="upload-staticwebsiteresults",
    bucket_name="staticwebsiteresults",
    action="put",
    action_operators=[nnunet_evaluation_notebook],
    file_white_tuples=(".html", ".pdf"),
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_gt_images >> get_ref_ct_from_gt >> dcm2nifti_gt >> seg_check_gt
get_ref_ct_from_gt >> dcmconverter_gt >> seg_check_gt >> evaluation

get_test_images >> get_ref_ct_from_test >> dcm2nifti_test >> seg_check_test
get_ref_ct_from_test >> dcmconverter_test >> seg_check_test >> evaluation

evaluation >> nnunet_evaluation_notebook >> put_to_minio >> put_report_to_minio >> clean
