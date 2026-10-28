"""Rebuild the nnU-Net dropdowns from MinIO and register raw datasets uploaded by hand."""

from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from kaapana_nnunetv2 import forms
from kaapana_nnunetv2.NnUNetV2Operator import NnUNetV2Operator

args = {
    "ui_visible": True,
    "ui_forms": forms.ui_forms("nnunetv2-refresh", forms.REFRESH, data_form={}),
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="nnunetv2-refresh",
    default_args=args,
    max_active_runs=1,
    schedule_interval=None,
    tags=["nnU-Net"],
)

NnUNetV2Operator(dag=dag, step="refresh")
