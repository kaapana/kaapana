"""nnUNetv2_train: one pod per selected fold, all folds of a run in parallel (as GPUs allow)."""

from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana_nnunetv2 import forms
from kaapana_nnunetv2.gpu import prepare_folds
from kaapana_nnunetv2.NnUNetV2Operator import NnUNetV2Operator

args = {
    "ui_visible": True,
    "ui_forms": forms.ui_forms("nnunetv2-train", forms.TRAIN, data_form={}),
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="nnunetv2-train",
    default_args=args,
    max_active_runs=5,
    concurrency=30,
    schedule_interval=None,
    tags=["nnU-Net"],
)

prepare = KaapanaPythonBaseOperator(dag=dag, name="prepare-folds", python_callable=prepare_folds)

# prepare-folds skips the unselected folds; the run succeeds when every selected fold succeeded
for fold in ("0", "1", "2", "3", "4", "all"):
    prepare >> NnUNetV2Operator(dag=dag, step="train", fold=fold, trigger_rule=TriggerRule.ALL_SUCCESS)
