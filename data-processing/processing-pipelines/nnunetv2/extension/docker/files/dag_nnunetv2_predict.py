"""nnU-Net prediction on DICOM images with a trained model; results go to the PACS as DICOM SEG."""

from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from kaapana_nnunetv2 import forms
from kaapana_nnunetv2.NnUNetV2Operator import NnUNetV2Operator

args = {
    "ui_visible": True,
    "ui_forms": forms.ui_forms("nnunetv2-predict", forms.PREDICT),
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="nnunetv2-predict",
    default_args=args,
    max_active_runs=10,
    schedule_interval=None,
    tags=["nnU-Net"],
)

NnUNetV2Operator(dag=dag, step="predict")
