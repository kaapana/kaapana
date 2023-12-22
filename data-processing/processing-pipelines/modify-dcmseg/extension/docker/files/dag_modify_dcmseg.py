from datetime import datetime, timedelta

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.Mask2nifitiOperator import Mask2nifitiOperator
from modify_dcmseg.LocalModifySegLabelNamesOperator import (
    LocalModifySegLabelNamesOperator,
)
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.MergeMasksOperator import MergeMasksOperator
from kaapana.operators.DcmModifyOperator import DcmModifyOperator
from airflow.utils.dates import days_ago
from airflow.models import DAG


ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "input": {
                "title": "Input Modality",
                "default": "SEG",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
                "required": True,
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
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
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
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="modify_segmentations",
    default_args=args,
    concurrency=10,
    max_active_runs=1,
    schedule_interval=None,
)

get_input = LocalGetInputDataOperator(
    dag=dag, name="get-input", check_modality=True, parallel_downloads=5
)

get_ref_ct_series_from_seg = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_input,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
    modality=None,
)

# # COMMENTED OUT BY DEFAULT: ONLY NECESSARY IF DICOM STANDARD FOR CT DATA IS VIOLATED
# # TODO: adjust subsequent operators and DAG flow:
# # - dcm2nifti_seg: dicom_operator=dcmodify
# # - nrrd2dcmSeg_multi: input_operator=dcmodify
# dcmodify = DcmModifyOperator(
#     dag=dag,
#     name="dcmodify-ct",
#     input_operator=get_ref_ct_series_from_seg,
#     dicom_tags_to_modify="(0020,0052)=RANDOM_UID;(0020,1040)=;(0020,0032)=0.000\\0.000\\0.000",
#     mode="insert",
# )

dcm2nifti_seg = Mask2nifitiOperator(
    dag=dag,
    input_operator=get_input,
    dicom_operator=get_ref_ct_series_from_seg,
)

fuse_masks = MergeMasksOperator(
    dag=dag,
    name="fuse-masks",
    input_operator=dcm2nifti_seg,
    mode="fuse",
)

combine_masks = MergeMasksOperator(
    dag=dag,
    name="combine-masks",
    input_operator=fuse_masks,
    mode="combine",
)

modify_seg_label_names = LocalModifySegLabelNamesOperator(
    dag=dag,
    input_operator=combine_masks,
    metainfo_input_operator=fuse_masks,
)

nrrd2dcmSeg_multi = Itk2DcmSegOperator(
    dag=dag,
    input_operator=get_ref_ct_series_from_seg,
    segmentation_operator=combine_masks,
    input_type="multi_label_seg",
    multi_label_seg_name="rename-seg-label-names",
    multi_label_seg_info_json="seg_info.json",
    skip_empty_slices=True,
    alg_name="modify-dcmseg",
)

# # COMMENTED OUT BY DEFAULT: ONLY NECESSARY IF DICOM STANDARD FOR CT DATA IS VIOLATED
# # TODO: adjust subsequent operators and DAG flow
# # - dicom_send: input_operator=dcmodify_seg
# dcmodify_seg = DcmModifyOperator(
#     dag=dag,
#     name="dcmodify-seg",
#     input_operator=nrrd2dcmSeg_multi,
#     gt_dicom_operator=get_input.operator_out_dir,
#     dicom_tags_to_modify="(0008,1115)=OVERWRITE",
#     mode="overwrite",
# )

dicom_send = DcmSendOperator(
    dag=dag,
    input_operator=nrrd2dcmSeg_multi,
    ae_title="modify-dcmseg",
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

######################################################################
###
# TODO: DECIDE FOR CORRECT DAG FLOW
###
######################################################################

# DEFAULT DAG FLOW
(
    get_input
    >> dcm2nifti_seg
    >> fuse_masks
    >> combine_masks
    >> modify_seg_label_names
    >> nrrd2dcmSeg_multi
    >> dicom_send
    >> clean
)
get_input >> get_ref_ct_series_from_seg >> nrrd2dcmSeg_multi
get_ref_ct_series_from_seg >> dcm2nifti_seg

# # DAG FLOW FOR DCM STANDARD VIOLATED DATA
# (
#     get_input
#     >> dcm2nifti_seg
#     >> fuse_masks
#     >> combine_masks
#     >> modify_seg_label_names
#     >> nrrd2dcmSeg_multi
#     >> dcmodify_seg
#     >> dicom_send
#     >> clean
# )
# get_input >> get_ref_ct_series_from_seg >> dcmodify >> nrrd2dcmSeg_multi
# dcmodify >> dcm2nifti_seg
