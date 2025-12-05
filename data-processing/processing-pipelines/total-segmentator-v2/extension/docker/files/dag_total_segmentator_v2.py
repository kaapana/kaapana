from datetime import timedelta
from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.exceptions import AirflowSkipException
from totalsegmentatorv2.GetZenodoModelOperator import GetZenodoModelOperator
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.LocalDagTriggerOperator import LocalDagTriggerOperator

max_active_runs = 10
concurrency = max_active_runs * 3
alg_name = "TotalSegmentator-v2"

model_dir='/models/total_segmentator_v2'
task_dict = {
    "total": "Dataset291_TotalSegmentator_part1_organs_1559subj,Dataset292_TotalSegmentator_part2_vertebrae_1532subj,Dataset293_TotalSegmentator_part3_cardiac_1559subj,"
             "Dataset294_TotalSegmentator_part4_muscles_1559subj,Dataset295_TotalSegmentator_part5_ribs_1559subj,Dataset298_TotalSegmentator_total_6mm_1559subj,"
             "Dataset297_TotalSegmentator_total_3mm_1559subj",
    "total_mr":"Dataset850_TotalSegMRI_part1_organs_1088subj,Dataset851_TotalSegMRI_part2_muscles_1088subj,Dataset852_TotalSegMRI_total_3mm_1088subj",
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

def check_subtask_callback(ds, **kwargs):
    subtask = kwargs["params"].get("subtask")
    conf = kwargs["dag_run"].conf
    tasks = conf["workflow_form"].get('tasks')
    if subtask not in tasks:
        raise AirflowSkipException(f"Subtask {subtask} skipped!")


for subtask in list(task_dict):
    check_subtask = KaapanaPythonBaseOperator(
        name=f"check-subtask-{subtask}",
        python_callable=check_subtask_callback,
        dag=dag,
        params={'subtask': subtask}
    )
    get_subtask_model = GetZenodoModelOperator(
        dag=dag,
        name=f"get_zenodo_model-{subtask}",
        model_dir=model_dir,
        task_ids=task_dict[subtask]
    )
    args = {'workflow_form': {'TASK': subtask,
                              'minio_prefix': f'radiomics-totalseg-v2-{subtask}'}}
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
