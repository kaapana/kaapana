"""Segmentations with overlaps or inconsistent names -> harmonized DICOM SEGs in a new Kaapana dataset."""

from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from kaapana_nnunetv2 import forms
from kaapana_nnunetv2.NnUNetV2Operator import NnUNetV2Operator

args = {
    "ui_visible": True,
    "ui_forms": forms.ui_forms("nnunetv2-harmonize-segmentations", forms.HARMONIZE, data_form=forms.DATASET_ONLY),
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="nnunetv2-harmonize-segmentations",
    default_args=args,
    max_active_runs=3,
    schedule_interval=None,
    tags=["nnU-Net"],
)

NnUNetV2Operator(dag=dag, step="harmonize")
