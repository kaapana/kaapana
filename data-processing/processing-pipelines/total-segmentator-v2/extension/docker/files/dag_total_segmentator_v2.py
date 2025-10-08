from datetime import timedelta
import os
from pathlib import Path
import glob
import shutil
from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.exceptions import AirflowSkipException

from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from totalsegmentator.TotalSegmentatorV2Operator import TotalSegmentatorV2Operator
from kaapana.operators.GetZenodoModelOperator import GetZenodoModelOperator
from kaapana.operators.MinioOperator import MinioOperator
from kaapana.operators.UpdateSegInfoJSONOperator import UpdateSegInfoJSONOperator
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.LocalDagTriggerOperator import LocalDagTriggerOperator
from pyradiomics.PyRadiomicsOperator import PyRadiomicsOperator

max_active_runs = 10
concurrency = max_active_runs * 3
alg_name = "TotalSegmentator-v2"

task_dict = {
    "total": '',
    "total_mr": "Dataset850_TotalSegMRI_part1_organs_1088subj,Dataset851_TotalSegMRI_part1_organs_1088subj,Dataset852_TotalSegMRI_total_3mm_1088subj",
    "body": "Dataset299_body_1559subj,Dataset300_body_6mm_1559subj",
    "body_mr": "Dataset597_mri_body_139subj,Dataset598_mri_body_6mm_139subj",
    "lung_vessels": "Dataset258_lung_vessels_248subj",
    "hip_implant": "Dataset260_hip_implant_71subj",
    "liver_segments": "Dataset570_ct_liver_segments",
    "vertebrae_mr": "Dataset756_mri_vertebrae_1076subj",
    "cerebral_bleed": "Dataset150_icb_v0",
    "pleural_pericard_effusion": "Dataset315_thoraxCT",
    "head_glands_cavities": "Dataset775_head_glands_cavities_492subj",
    "head_muscles": "Dataset777_head_muscles_492subj",
    "headneck_bones_vessels": "Dataset776_headneck_bones_vessels_492subj",
    "headneck_muscles": "Dataset778_headneck_muscles_part1_492subj,Dataset779_headneck_muscles_part2_492subj",
    "liver_vessels": "Dataset008_HepaticVessel",
    "oculomotor_muscles": "Dataset351_oculomotor_muscles_18subj",
    "lung_nodules": "Dataset913_lung_nodules",
    "kidney_cysts": "Dataset789_kidney_cyst_501subj",
    "breasts": "Dataset527_breasts_1559subj",
    "liver_segments_mr": "Dataset576_mri_liver_segments_120subj",
    "craniofacial_structures": "Dataset115_mandible",
    "abdominal_muscles": "Dataset952_abdominal_muscles_167subj",
    "teeth": "Dataset113_ToothFairy3"
}

ui_forms = {
    "documentation_form": {
        "path": "/user_guide/extensions.html#totalsegmentator",
    },
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
            "tasks": {
                "title": "Sub-Tasks",
                "description": "Choose one or more sub-tasks for processing",
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": list(task_dict)
                },
                "default": ["total"],
                "readOnly": False
            },
            "bodyseg": {
                "title": "--body_seg",
                "description": "Do initial rough body segmentation and crop image to body region.",
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
            "input": {
                "title": "Input",
                "description": "Input-data modality",
                "type": "string",
                "enum": ["CT", "MR"],
                "readOnly": False,
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
    dag_id="total-segmentator-v2",
    default_args=args,
    concurrency=concurrency,
    max_active_runs=max_active_runs,
    schedule_interval=None,
)

get_total_segmentator_model = GetZenodoModelOperator(
    dag=dag,
    model_dir='/models/totalsegmentatorv2',
    task_ids="Dataset291_TotalSegmentator_part1_organs_1559subj,Dataset292_TotalSegmentator_part2_vertebrae_1532subj,Dataset293_TotalSegmentator_part3_cardiac_1559subj,Dataset294_TotalSegmentator_part4_muscles_1559subj,"
    "Dataset295_TotalSegmentator_part5_ribs_1559subj,Dataset298_TotalSegmentator_total_6mm_1559subj,Dataset297_TotalSegmentator_total_3mm_1559subj"
)

get_input = GetInputOperator(dag=dag, parallel_downloads=5,
                             check_modality=True, data_type='all')


def move_metadata_json(ds, **kwargs):
    batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME
    batch_folder = [f for f in glob.glob(os.path.join(batch_dir, "*"))]
    for batch_element_dir in batch_folder:
        json_dir = Path(batch_element_dir) / get_input.operator_out_dir
        dest_dir = Path(batch_element_dir) / dcm2nifti.operator_out_dir
        json_files = [f for f in json_dir.glob("*.json")]
        print('from callback:', json_files)
        shutil.copy(json_files[0], dest_dir)


put_metadata_json = KaapanaPythonBaseOperator(
    name="put_metajson",
    python_callable=move_metadata_json,
    dag=dag,
)

dcm2nifti = DcmConverterOperator(
    dag=dag,
    input_operator=get_input,
    output_format="nii.gz",
)

ta = "total"
total_segmentator = TotalSegmentatorV2Operator(
    dag=dag, task=ta, input_operator=dcm2nifti, multilabel=True
)

combine_masks = UpdateSegInfoJSONOperator(
    dag=dag,
    input_operator=total_segmentator,
    parallel_id=ta,
    mode='update_json'
)

nrrd2dcmSeg_multi = Itk2DcmSegOperator(
    dag=dag,
    input_operator=get_input,
    segmentation_operator=combine_masks,
    input_type="multi_label_seg",
    multi_label_seg_name=alg_name,
    multi_label_seg_info_json="seg_info.json",
    skip_empty_slices=True,
    parallel_id=ta,
    alg_name=f"{alg_name}-{ta}",
)

dcmseg_send = DcmSendOperator(
    dag=dag,
    input_operator=nrrd2dcmSeg_multi,
    parallel_id=ta,
)

pyradiomics_total = PyRadiomicsOperator(
    dag=dag,
    input_operator=dcm2nifti,
    segmentation_operator=total_segmentator,
    parallel_id=ta,
)

put_to_minio = MinioOperator(
    dag=dag,
    action="put",
    minio_prefix="radiomics-totalsegmentator-v2",
    batch_input_operators=[pyradiomics_total],
    whitelisted_file_extensions=[".json"],
    trigger_rule="none_failed_min_one_success",
)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True,
    trigger_rule="none_failed",
)

def check_subtask_callback(ds, **kwargs):
    subtask = kwargs["params"].get("subtask")
    conf = kwargs["dag_run"].conf
    tasks = conf["workflow_form"].get('tasks')
    if subtask not in tasks:
        raise AirflowSkipException(f"Subtask {subtask} skipped!")


for subtask in list(task_dict):
    if subtask == 'total':
        continue
    check_subtask = KaapanaPythonBaseOperator(
        name=f"check-subtask-{subtask}",
        python_callable=check_subtask_callback,
        dag=dag,
        params={'subtask': subtask}
    )
    get_subtask_model = GetZenodoModelOperator(
        dag=dag,
        name=f"get_zenodo_model-{subtask}",
        model_dir='/models/totalsegmentatorv2',
        task_ids=task_dict[subtask]
    )
    args = {'workflow_form': {'TASK': subtask}}
    subtask_dag = LocalDagTriggerOperator(
        dag=dag,
        input_operator=None,
        trigger_dag_id="total-segmentator-v2-subtask",
        trigger_mode="single",
        wait_till_done=True,
        use_dcm_files=False,
        delay=10,
        task_id=f"trigger_totalseg_{subtask}",
        extra_conf=args
    )
    check_subtask >> get_subtask_model >> subtask_dag

get_total_segmentator_model >> total_segmentator
(
    get_input
    >> dcm2nifti
    >> put_metadata_json
    >> total_segmentator
    >> combine_masks
    >> nrrd2dcmSeg_multi
    >> dcmseg_send
    >> clean
)
total_segmentator >> pyradiomics_total >> put_to_minio
