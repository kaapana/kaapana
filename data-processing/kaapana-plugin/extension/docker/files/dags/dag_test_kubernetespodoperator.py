from datetime import datetime, timedelta
from airflow.utils.dates import days_ago
from airflow.models import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import V1LocalObjectReference, V1ResourceRequirements


args = {
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}


with DAG("test-KubernetesPodOperator") as dag:
    task = KubernetesPodOperator(
        task_id="hello-word",
        name="hello-world",
        image="registry.hzdr.de/lorenz.feineis/kaapana-feineis-dev/test-mask2nifti:latest",
        cmds=["/usr/bin/sleep"],
        arguments=["120"],
        namespace="project-admin",
        image_pull_secrets=[V1LocalObjectReference(name="registry-secret")],
        get_logs=True,
        container_logs=True,
        base_container_name="hello-world",
        container_resources=V1ResourceRequirements(
            limits={"memory": "256Mi", "nvidia.com/gpu": 1}
        ),
        on_finish_action="keep_pod",
    )

    task_two = KubernetesPodOperator(
        task_id="hello-word-2",
        name="hello-world-2",
        image="registry.hzdr.de/lorenz.feineis/kaapana-feineis-dev/test-mask2nifti:latest",
        cmds=["/usr/bin/sleep"],
        arguments=["120"],
        namespace="project-admin",
        image_pull_secrets=[V1LocalObjectReference(name="registry-secret")],
        get_logs=True,
        container_logs=True,
        base_container_name="hello-world",
        container_resources=V1ResourceRequirements(
            limits={"memory": "256Mi", "nvidia.com/gpu": 1}
        ),
        on_finish_action="keep_pod",
    )
