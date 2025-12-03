"""
{{ workflow_display_name }} - Airflow Workflow

Created: {{ date }}
"""

from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from task_api_operators.KaapanaTaskOperator import KaapanaTaskOperator

args = {
    "ui_visible": True,
    "owner": "kaapana",
}

with DAG(
    dag_id="{{ workflow_name }}",
    default_args=args,
    schedule_interval=None,
    catchup=False,
    tags=["example", "{{ workflow_engine }}"],
) as dag:
    example_task = KaapanaTaskOperator(
        task_id="example_task",
        image=f"{DEFAULT_REGISTRY}/example-container:{KAAPANA_BUILD_VERSION}",
        taskTemplate="example-task-template",
        execution_timeout=timedelta(minutes=10),
    )
