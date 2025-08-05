from datetime import datetime, timedelta
from airflow.utils.dates import days_ago
from airflow.models import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from taskctl.model import Task, IOChannel
from kubernetes.client import V1LocalObjectReference

args = {
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="tag-dataset",
    default_args=args,
    concurrency=10,
    max_active_runs=1,
    schedule_interval=None,
)


my_task = Task(
    name="test-taskctl",
    image="registry.hzdr.de/lorenz.feineis/kaapana-feineis-dev/dummy-task:latest",
    inputs={"workflow-dir": IOChannel(local_path="")},
    outputs=[],
    env={},
)


with DAG("test-KubernetesPodOperator") as dag:
    task = KubernetesPodOperator(
        task_id="hello-word",
        name="hello-world",
        image="registry.hzdr.de/lorenz.feineis/kaapana-feineis-dev/test-mask2nifti:latest",
        cmds=["/bin/bash", "-c"],
        arguments=["echo hello world!"],
        namespace="project-admin",
        image_pull_secrets=[V1LocalObjectReference(name="registry-secret")],
        get_logs=True,
        container_logs=True,
        base_container_name="hello-world",
        on_finish_action="keep_pod",
    )
