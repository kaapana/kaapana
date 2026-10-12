from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago

from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from autosegmentationpipeline.BodyPartInferenceOperator import (
    BODY_PART_TO_CANONICAL,
    infer_body_part_callback,
)
from autosegmentationpipeline.DynamicConfDagTriggerOperator import (
    DynamicConfDagTriggerOperator,
)

"""
Infers which body part a radiology (CT/MR) series covers - by looking at the
DICOM metadata of the matching pathology (SM) study for the same patient via
infer_body_part_callback - then runs total-segmentator-v2 with a task list
chosen accordingly. This is the "resolve the anatomical region" step the
combined radiology/pathology viewer's organ-to-slide linking depends on.

Ported from combinedmodalityviewer's Kaapana_Extension/Auto-segmentation-pipeline,
which forked Kaapana's older v1 total-segmentator wholesale (duplicated
operator, Dockerfile, lookup tables, pyradiomics) to add this body-part
filtering. Retargeted onto total-segmentator-v2 instead: that DAG already
fans out over a workflow_form.tasks list and is designed to be triggered with
a custom conf (it already uses LocalDagTriggerOperator internally for its own
per-task fan-out - see dag_total_segmentator_v2.py). So this pipeline doesn't
need to fork TotalSegmentator again at all - it's a thin orchestration DAG
that triggers the existing total-segmentator-v2 DAG, and inherits all of its
own future improvements automatically.
"""

max_active_runs = 10
concurrency = max_active_runs * 3

# v1's canonical body parts don't map 1:1 onto total-segmentator-v2's task_dict
# keys (dag_total_segmentator_v2.py) - v2's "total"/"total_mr" task already
# broadly covers organs/vertebrae/cardiac/muscles/ribs, so only body parts
# with a genuinely distinct specialized v2 task get an extra task added on
# top. Several of these specialized tasks only exist for CT (task_dict has no
# MR-trained model for them) - None in that case means "skip the extra task
# for this modality", not "fall back to CT". Easy to extend later
# (hip_implant/cerebral_bleed/pleural_pericard_effusion are available v2
# tasks too, just not currently inferable from the DICOM tags
# BodyPartInferenceOperator checks).
BODY_PART_TO_V2_EXTRA_TASK = {
    "lung": {"CT": "lung_vessels", "MR": None},
    "liver": {"CT": "liver_segments", "MR": "liver_segments_mr"},
}

# roi_subset restricts total-segmentator-v2's base "total"/"total_mr" task to
# just the structure(s) matching the inferred/forced body part, instead of
# always segmenting and exposing all 117 (CT) / 50 (MR) structures - so OHIF
# only shows the one organ a pathology slide actually exists for. Label names
# confirmed against processing-containers/total-segmentator/files/seg_info_lookup.json
# ("total"/"total_mr" entries' label_name values) - not every canonical body
# part maps onto a single label (e.g. "lung" needs all 5 lobes), and
# total_mr's label set is smaller than total's (no lung lobes at all, hence
# None for MR - falls back to the unrestricted base task rather than passing
# a roi_subset that would silently match nothing).
CANONICAL_TO_ROI_SUBSET = {
    "heart": {"CT": ["heart"], "MR": ["heart"]},
    "liver": {"CT": ["liver"], "MR": ["liver"]},
    "spleen": {"CT": ["spleen"], "MR": ["spleen"]},
    "kidney": {"CT": ["kidney_left", "kidney_right"], "MR": ["kidney_left", "kidney_right"]},
    "lung": {
        "CT": [
            "lung_upper_lobe_left",
            "lung_lower_lobe_left",
            "lung_upper_lobe_right",
            "lung_middle_lobe_right",
            "lung_lower_lobe_right",
        ],
        "MR": None,
    },
    "aorta": {"CT": ["aorta"], "MR": ["aorta"]},
    "brain": {"CT": ["brain"], "MR": ["brain"]},
    "prostate": {"CT": ["prostate"], "MR": ["prostate"]},
}


def resolve_v2_tasks(body_part, modality) -> list:
    base_task = "total_mr" if modality == "MR" else "total"
    tasks = [base_task]
    extra_task = BODY_PART_TO_V2_EXTRA_TASK.get(body_part, {}).get(modality)
    if extra_task:
        tasks.append(extra_task)
    return tasks


def resolve_roi_subset(body_part, modality) -> list | None:
    return CANONICAL_TO_ROI_SUBSET.get(body_part, {}).get(modality)


def build_total_segmentator_v2_conf(kwargs) -> dict:
    body_part = kwargs["ti"].xcom_pull(task_ids="infer_body_part")
    # Pushed by infer_body_part (BodyPartInferenceOperator.py) under its own
    # xcom key, from the actual local DICOM file's Modality tag - total-
    # segmentator-v2's own get-input-data task rejects a series whose
    # modality isn't in this list, so this can't be hardcoded to "CT", and
    # which v2 task names are even valid depends on it too (e.g. "total_mr"
    # vs "total" - see resolve_v2_tasks() above).
    modality = kwargs["ti"].xcom_pull(task_ids="infer_body_part", key="modality") or "CT"
    tasks = resolve_v2_tasks(body_part, modality)
    workflow_form = {
        "tasks": tasks,
        "input": modality,
        "nr_thr_resamp": 1,
        "nr_thr_saving": 6,
    }
    roi_subset = resolve_roi_subset(body_part, modality)
    if roi_subset:
        # A plain space-separated string, not a Python list: KaapanaBaseOperator
        # forwards every workflow_form key into the container as str(value)
        # verbatim (see KaapanaBaseOperator.py's execute(), workflow_form loop),
        # and the total-segmentator-v2 container's own ROI_SUBSET env var is
        # parsed by splitting on whitespace - a list here would show up as
        # Python's "['liver']" repr instead, which wouldn't parse correctly.
        workflow_form["roi_subset"] = " ".join(roi_subset)
        # roi_subset alone only filters the OUTPUT of the standard "total"
        # task - every one of its underlying sub-models still runs at full
        # resolution regardless, so it doesn't actually save any time by
        # itself. --fast is what makes roi_subset genuinely faster: per
        # total-segmentator-v2's own container (ROI_SUBSET's docstring in
        # start-total-segmentator-v2.py), the 1.5mm fast model only runs the
        # specific sub-models needed for the requested ROIs. Since the whole
        # point of restricting to one organ here is quick iteration during
        # testing (not final-quality output), bundle this in rather than
        # requiring a separate manual toggle.
        workflow_form["fast"] = True
    return {"workflow_form": workflow_form}


ui_forms = {
    "documentation_form": {
        "path": "/user_guide/extensions.html#totalsegmentator",
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "input": {
                "title": "Input",
                "default": "CT",
                "description": "Input-data modality",
                "type": "string",
                "readOnly": True,
            },
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
                "readOnly": True,
            },
            "body_part": {
                "title": "Body part",
                "description": "Force a body part instead of inferring it from the "
                "patient's pathology (SM) metadata - leave empty to auto-infer.",
                "type": "string",
                "default": "",
                "enum": [""] + sorted(set(BODY_PART_TO_CANONICAL.values())),
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
    dag_id="auto-segmentation-pipeline",
    default_args=args,
    concurrency=concurrency,
    max_active_runs=max_active_runs,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag, parallel_downloads=5, check_modality=True)

infer_body_part = KaapanaPythonBaseOperator(
    dag=dag,
    name="infer_body_part",
    python_callable=infer_body_part_callback,
    params={"dicom_operator_out_dir": get_input.operator_out_dir},
    input_operator=get_input,
)

trigger_total_segmentator_v2 = DynamicConfDagTriggerOperator(
    dag=dag,
    trigger_dag_id="total-segmentator-v2",
    trigger_mode="single",
    wait_till_done=True,
    use_dcm_files=False,
    delay=10,
    extra_conf_callable=build_total_segmentator_v2_conf,
)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True,
    trigger_rule="none_failed",
)

get_input >> infer_body_part >> trigger_total_segmentator_v2 >> clean
