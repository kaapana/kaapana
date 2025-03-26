from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.LocalMinioDataTransferOperator import LocalMinioDataTransferOperator
import os
import json
import shutil
from pathlib import Path
import glob

log = LoggingMixin().log
import requests

def get_all_projects():
    try:
        r = requests.get("http://aii-service.services.svc:8080/projects")
        projects = r.json()
        project_names = [project["name"] for project in projects]
        return project_names

    except Exception as e:
        print("Error in get projects: ", e)
        return []

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties":  {     
            "projects": {
                "title": "Destination Projects",
                "description": "The project(s) to which the data will be copied.",
                "type": "array",
                "items": {"type": "string", "enum": get_all_projects()},
                "required": True,
            },
        },
    },
    "backend_form":{
        "include-dataset": False,
        "backend-route": "/storage/projectbucket"
    }
}

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="project-minio-transfer",
    default_args=args,
    concurrency=10,
    max_active_runs=1,
    schedule_interval=None,
)

copy_files_minio = LocalMinioDataTransferOperator(dag=dag)