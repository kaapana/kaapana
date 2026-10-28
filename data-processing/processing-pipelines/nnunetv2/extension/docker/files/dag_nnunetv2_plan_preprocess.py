"""nnU-Net fingerprint extraction, experiment planning and preprocessing; each step can run on its own."""

from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from kaapana_nnunetv2 import forms
from kaapana_nnunetv2.NnUNetV2Operator import NnUNetV2Operator

args = {
    "ui_visible": True,
    "ui_forms": forms.ui_forms("nnunetv2-plan-preprocess", forms.PLAN_PREPROCESS, data_form={}),
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="nnunetv2-plan-preprocess",
    default_args=args,
    max_active_runs=3,
    schedule_interval=None,
    tags=["nnU-Net"],
)

NnUNetV2Operator(dag=dag, step="plan_preprocess")
