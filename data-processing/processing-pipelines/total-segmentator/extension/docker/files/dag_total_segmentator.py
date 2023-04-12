from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago

from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from totalsegmentator.LocalGetTotalSegmentatorModelsOperator import (
    LocalGetTotalSegmentatorModelsOperator,
)
from totalsegmentator.TotalSegmentatorOperator import TotalSegmentatorOperator
from kaapana.operators.GetZenodoModelOperator import GetZenodoModelOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalCombineMasksOperator import LocalCombineMasksOperator
from pyradiomics.PyRadiomicsOperator import PyRadiomicsOperator

max_active_runs = 3
concurrency = max_active_runs * 3

ui_forms = {
    "publication_form": {
        "type": "object",
        "properties": {
            "title": {
                "title": "Title",
                "default": "TotalSegmentator: robust segmentation of 104 anatomical structures in CT images",
                "type": "string",
                "readOnly": True,
            },
            "authors": {
                "title": "Authors",
                "default": "Wasserthal J., Meyer M., Breit H., Cyriac J., Yang S., Segeroth M.",
                "type": "string",
                "readOnly": True,
            },
            "link": {
                "title": "DOI",
                "default": "https://arxiv.org/abs/2208.05868",
                "description": "DOI",
                "type": "string",
                "readOnly": True,
            },
            "confirmation": {
                "title": "Accept",
                "default": False,
                "type": "boolean",
                "readOnly": False,
                "required": True,
            },
        },
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "fast": {
                "title": "--fast",
                "description": "Run faster lower resolution model.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "preview": {
                "title": "--preview",
                "description": "Generate a png preview of segmentation.",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "statistics": {
                "title": "--statistics",
                "description": "Calc volume (in mm3) and mean intensity. Results will be in statistics.json.",
                "type": "boolean",
                "default": True,
                "readOnly": False,
            },
            "radiomics": {
                "title": "--radiomics",
                "description": "Calc radiomics features. Requires pyradiomics. Results will be in statistics_radiomics.json.",
                "type": "boolean",
                "default": True,
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
                "default": True,
                "readOnly": False,
            },
            "cerebral_bleed": {
                "title": "enable lung_vessels",
                "description": "Add segmentations for intracerebral_hemorrhage.",
                "type": "boolean",
                "default": True,
                "readOnly": False,
            },
            "hip_implant": {
                "title": "enable hip_implant",
                "description": "Add segmentations for hip_implant.",
                "type": "boolean",
                "default": True,
                "readOnly": False,
            },
            "coronary_arteries": {
                "title": "enable coronary_arteries",
                "description": "Add segmentations for coronary_arteries.",
                "type": "boolean",
                "default": True,
                "readOnly": False,
            },
            "body": {
                "title": "enable body",
                "description": "Add segmentations for body, body_trunc, body_extremities, skin",
                "type": "boolean",
                "default": True,
                "readOnly": False,
            },
            "pleural_pericard_effusion": {
                "title": "enable pleural_pericard_effusion",
                "description": "Add segmentations for pleural_effusion and pericardial_effusion.",
                "type": "boolean",
                "default": True,
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
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
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
    "retry_delay": timedelta(seconds=60),
}

dag = DAG(
    dag_id="total-segmentator",
    default_args=args,
    concurrency=concurrency,
    max_active_runs=max_active_runs,
    schedule_interval=None,
)

get_total_segmentator_model = GetZenodoModelOperator(
    dag=dag,
    model_dir="/models/total_segmentator/nnUNet",
    task_ids="Task251_TotalSegmentator_part1_organs_1139subj,Task252_TotalSegmentator_part2_vertebrae_1139subj,Task253_TotalSegmentator_part3_cardiac_1139subj,Task254_TotalSegmentator_part4_muscles_1139subj,Task255_TotalSegmentator_part5_ribs_1139subj,Task256_TotalSegmentator_3mm_1139subj,Task258_lung_vessels_248subj,Task150_icb_v0,Task260_hip_implant_71subj,Task269_Body_extrem_6mm_1200subj,Task273_Body_extrem_1259subj",
)

get_input = LocalGetInputDataOperator(
    dag=dag, parallel_downloads=5, check_modality=True
)

dcm2nifti = DcmConverterOperator(
    dag=dag,
    input_operator=get_input,
    output_format="nii.gz",
)

ta = "total"
total_segmentator_0 = TotalSegmentatorOperator(
    dag=dag, task=ta, input_operator=dcm2nifti
)

ta = "lung_vessels"
total_segmentator_1 = TotalSegmentatorOperator(
    dag=dag,
    task=ta,
    input_operator=dcm2nifti,
    operator_out_dir=total_segmentator_0.operator_out_dir,
    delete_output_on_start=False,
    parallel_id=ta,
)

ta = "cerebral_bleed"
total_segmentator_2 = TotalSegmentatorOperator(
    dag=dag,
    task=ta,
    input_operator=dcm2nifti,
    operator_out_dir=total_segmentator_0.operator_out_dir,
    delete_output_on_start=False,
    parallel_id=ta,
)

ta = "hip_implant"
total_segmentator_3 = TotalSegmentatorOperator(
    dag=dag,
    task=ta,
    input_operator=dcm2nifti,
    operator_out_dir=total_segmentator_0.operator_out_dir,
    delete_output_on_start=False,
    parallel_id=ta,
)

ta = "coronary_arteries"
total_segmentator_4 = TotalSegmentatorOperator(
    dag=dag,
    task=ta,
    input_operator=dcm2nifti,
    operator_out_dir=total_segmentator_0.operator_out_dir,
    delete_output_on_start=False,
    parallel_id=ta,
)

ta = "body"
total_segmentator_5 = TotalSegmentatorOperator(
    dag=dag,
    task=ta,
    input_operator=dcm2nifti,
    operator_out_dir=total_segmentator_0.operator_out_dir,
    delete_output_on_start=False,
    parallel_id=ta,
)

ta = "pleural_pericard_effusion"
total_segmentator_6 = TotalSegmentatorOperator(
    dag=dag,
    task=ta,
    input_operator=dcm2nifti,
    operator_out_dir=total_segmentator_0.operator_out_dir,
    delete_output_on_start=False,
    parallel_id=ta,
)

combine_masks = LocalCombineMasksOperator(
    dag=dag,
    combine_operators=[total_segmentator_0],
    trigger_rule="all_done",
)

alg_name = "TotalSegmentator"
nrrd2dcmSeg_multi = Itk2DcmSegOperator(
    dag=dag,
    input_operator=get_input,
    segmentation_operator=combine_masks,
    input_type="multi_label_seg",
    multi_label_seg_name=alg_name,
    multi_label_seg_info_json="seg_info.json",
    skip_empty_slices=True,
    alg_name=alg_name,
)

# pyradiomics = PyRadiomicsOperator(
#     dag=dag,
#     input_operator=dcm2nifti,
#     segmentation_operator=total_segmentator,
# )

# put_to_minio = LocalMinioOperator(dag=dag, action='put', action_operators=[pyradiomics], file_white_tuples=('.json'))
dcmseg_send_multi = DcmSendOperator(dag=dag, input_operator=nrrd2dcmSeg_multi)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_total_segmentator_model >> total_segmentator_0
get_input >> dcm2nifti >> total_segmentator_0

total_segmentator_0 >> total_segmentator_1 >> combine_masks
total_segmentator_0 >> total_segmentator_2 >> combine_masks
total_segmentator_0 >> total_segmentator_3 >> combine_masks
total_segmentator_0 >> total_segmentator_4 >> combine_masks
total_segmentator_0 >> total_segmentator_5 >> combine_masks
total_segmentator_0 >> total_segmentator_6 >> combine_masks
combine_masks >> nrrd2dcmSeg_multi >> dcmseg_send_multi >> clean
# total_segmentator >> pyradiomics >> put_to_minio >> clean
