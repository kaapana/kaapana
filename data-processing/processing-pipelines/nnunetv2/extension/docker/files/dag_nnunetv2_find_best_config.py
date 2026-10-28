"""nnUNetv2_find_best_configuration: compare configurations by cross-validation, determine postprocessing and ensembles."""

from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from kaapana_nnunetv2 import forms
from kaapana_nnunetv2.NnUNetV2Operator import NnUNetV2Operator

args = {
    "ui_visible": True,
    "ui_forms": forms.ui_forms("nnunetv2-find-best-config", forms.FIND_BEST_CONFIG, data_form={}),
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="nnunetv2-find-best-config",
    default_args=args,
    max_active_runs=3,
    schedule_interval=None,
    tags=["nnU-Net"],
)

NnUNetV2Operator(dag=dag, step="find_best_config")
