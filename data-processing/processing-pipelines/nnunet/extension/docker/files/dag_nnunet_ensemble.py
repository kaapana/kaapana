from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from nnunet.DiceEvaluationOperator import DiceEvaluationOperator
from nnunet.LocalDataorganizerOperator import LocalDataorganizerOperator
from nnunet.NnUnetOperator import NnUnetOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from nnunet.LocalSortGtOperator import LocalSortGtOperator
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator
from kaapana.operators.Mask2nifitiOperator import Mask2nifitiOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.JupyterlabReportingOperator import JupyterlabReportingOperator
from nnunet.LocalModelGetInputDataOperator import LocalModelGetInputDataOperator
from nnunet.NnUnetModelOperator import NnUnetModelOperator
from nnunet.getTasks import get_available_protocol_names

# from kaapana.operators.LocalPatchedGetInputDataOperator import LocalPatchedGetInputDataOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from nnunet.SegCheckOperator import SegCheckOperator

from kaapana.operators.MergeMasksOperator import MergeMasksOperator
from kaapana.operators.LocalModifySegLabelNamesOperator import (
    LocalModifySegLabelNamesOperator,
)
from kaapana.operators.LocalFilterMasksOperator import LocalFilterMasksOperator

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
            # "input": {
            #     "title": "Input Modality",
            #     "default": "OT",
            #     "description": "Expected input modality.",
            #     "type": "string",
            #     "readOnly": True,
            # },
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
                "default": default_interpolation_order,
                "description": "Set interpolation_order.",
                "enum": ["default", "0", "1", "2", "3"],
                "type": "string",
                "readOnly": False,
                "required": True,
            },
            "inf_threads_prep": {
                "title": "Pre-processing threads",
                "type": "integer",
                "default": default_prep_thread_count,
                "description": "Set pre-processing thread count.",
                "required": True,
            },
            "inf_threads_nifti": {
                "title": "NIFTI threads",
                "type": "integer",
                "description": "Set NIFTI export thread count.",
                "default": default_nifti_thread_count,
                "required": True,
            },
            "input": {
                "title": "Input Modality",
                "default": "SEG",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
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
    dag_id="nnunet-ensemble",
    default_args=args,
    concurrency=3,
    max_active_runs=2,
    schedule_interval=None,
)

get_test_images = LocalGetInputDataOperator(
    dag=dag,
    name="nnunet-dataset",
    batch_name="nnunet-dataset",
    dataset_limit=None,
    parallel_downloads=5,
    check_modality=False,
)

# get_test_images = LocalGetRefSeriesOperator(
#     dag=dag,
#     name="nnunet-dataset",
#     target_level="batch",
#     expected_file_count="all",
#     limit_file_count=5,
#     dicom_tags=[
#         {
#             'id': 'ClinicalTrialProtocolID',
#             'value': 'tcia-lymph'
#         },
#         {
#             'id': 'Modality',
#             'value': 'SEG'
#         },
#     ],
#     modality=None,
#     search_policy=None,
#     parallel_downloads=5,
#     delete_input_on_success=True
# )

sort_gt = LocalSortGtOperator(
    dag=dag, batch_name="nnunet-dataset", input_operator=get_test_images
)


get_ref_ct_series_from_gt = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_test_images,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
    modality=None,
    batch_name=str(get_test_images.operator_out_dir),
    delete_input_on_success=False,
)

dcm2nifti_gt = Mask2nifitiOperator(
    dag=dag,
    dicom_operator=get_ref_ct_series_from_gt,
    input_operator=get_test_images,
    batch_name=str(get_test_images.operator_out_dir),
    seg_filter=organ_filter,
    parallel_id="gt",
)

filter_gt = LocalFilterMasksOperator(
    dag=dag,
    name="filter-masks",
    input_operator=dcm2nifti_gt,
    # label_filter_key="gt_label_filter",
    batch_name="nnunet-dataset",
)

fuse_gt = MergeMasksOperator(
    dag=dag,
    name="fuse-masks",
    input_operator=filter_gt,
    mode="fuse",
    trigger_rule="all_done",
    batch_name="nnunet-dataset",
)

rename_gt = LocalModifySegLabelNamesOperator(
    dag=dag,
    name="rename-masks",
    input_operator=fuse_gt,
    metainfo_input_operator=fuse_gt,
    results_to_in_dir=False,
    write_seginfo_results=False,
    write_metainfo_results=True,
    trigger_rule="all_done",
    batch_name="nnunet-dataset",
)

dcm2nifti_ct = DcmConverterOperator(
    dag=dag,
    input_operator=get_ref_ct_series_from_gt,
    parallel_id="ct",
    parallel_processes=parallel_processes,
    batch_name=str(get_test_images.operator_out_dir),
    output_format="nii.gz",
)

get_input = LocalModelGetInputDataOperator(
    dag=dag, name="get-models", check_modality=True, parallel_downloads=5
)

dcm2bin = Bin2DcmOperator(
    dag=dag, input_operator=get_input, name="extract-binary", file_extensions="*.dcm"
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
)

do_inference = LocalDataorganizerOperator(
    dag=dag,
    input_operator=nnunet_predict,
    mode="batchelement2batchelement",
    target_batchname=str(get_test_images.operator_out_dir),
    parallel_id="inference",
)

seg_check_inference = SegCheckOperator(
    dag=dag,
    input_operator=do_inference,
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
    batch_name=str(get_test_images.operator_out_dir),
    parallel_id="inference",
)

seg_check_gt = SegCheckOperator(
    dag=dag,
    input_operator=rename_gt,
    original_img_operator=dcm2nifti_ct,
    target_dict_operator=seg_check_inference,
    parallel_processes=parallel_processes,
    max_overlap_percentage=100,
    merge_found_niftis=True,
    delete_merged_data=False,
    fail_if_overlap=False,
    fail_if_label_already_present=False,
    fail_if_label_id_not_extractable=False,
    force_same_labels=False,
    batch_name=str(get_test_images.operator_out_dir),
    parallel_id="gt",
)

nnunet_ensemble = NnUnetOperator(
    dag=dag,
    input_operator=nnunet_predict,
    mode="ensemble",
    prep_min_combination=None,
    inf_threads_nifti=1,
)

do_ensemble = LocalDataorganizerOperator(
    dag=dag,
    input_operator=nnunet_ensemble,
    mode="batch2batchelement",
    target_batchname=str(get_test_images.operator_out_dir),
    parallel_id="ensemble",
)

seg_check_ensemble = SegCheckOperator(
    dag=dag,
    input_operator=do_ensemble,
    original_img_operator=dcm2nifti_ct,
    parallel_processes=parallel_processes,
    max_overlap_percentage=100,
    target_dict_operator=seg_check_inference,
    merge_found_niftis=False,
    delete_merged_data=False,
    fail_if_overlap=False,
    fail_if_label_already_present=False,
    fail_if_label_id_not_extractable=False,
    force_same_labels=False,
    batch_name=str(get_test_images.operator_out_dir),
    parallel_id="ensemble",
)

evaluation = DiceEvaluationOperator(
    dag=dag,
    anonymize=True,
    gt_operator=seg_check_gt,
    input_operator=seg_check_inference,
    ensemble_operator=seg_check_ensemble,
    parallel_processes=1,
    trigger_rule="all_done",
    batch_name=str(get_test_images.operator_out_dir),
)

get_notebooks_from_minio = LocalMinioOperator(
    dag=dag,
    name="nnunet-get-notebook-from-minio",
    bucket_name="analysis-scripts",
    action="get",
    action_files=["run_nnunet_evaluation_notebook.ipynb"],
)

nnunet_evaluation_notebook = JupyterlabReportingOperator(
    dag=dag,
    name="nnunet-evaluation-notebook",
    input_operator=evaluation,
    notebook_filename="run_nnunet_evaluation_notebook.ipynb",
    output_format="html,pdf",
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

(
    get_test_images
    >> sort_gt
    >> get_ref_ct_series_from_gt
    >> dcm2nifti_gt
    >> filter_gt
    >> fuse_gt
    >> rename_gt
    >> seg_check_gt
    >> evaluation
)
(
    get_input
    >> dcm2bin
    >> extract_model
    >> nnunet_predict
    >> nnunet_ensemble
    >> do_ensemble
    >> seg_check_ensemble
    >> evaluation
)
(nnunet_predict >> do_inference >> seg_check_inference >> evaluation)
(get_ref_ct_series_from_gt >> dcm2nifti_ct >> nnunet_predict)

seg_check_inference >> seg_check_gt
seg_check_inference >> seg_check_ensemble
(
    seg_check_inference
    >> evaluation
    >> get_notebooks_from_minio
    >> nnunet_evaluation_notebook
    >> put_to_minio
    >> put_report_to_minio
    >> clean
)
