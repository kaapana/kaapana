from kaapana.operators.ZipUnzipOperator import ZipUnzipOperator
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.models import DAG
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalTaggingOperator import LocalTaggingOperator
from doccano.LocalDoccanoDownloadDatasetOperator import (
    LocalDoccanoDownloadDatasetOperator,
)
from doccano.ProcessStudyIdsOperator import ProcessStudyIdsOperator
from datetime import timedelta

log = LoggingMixin().log

args = {
    "ui_visible": False,
    "owner": "system",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="service-parse-doccano-tokens",
    default_args=args,
    schedule_interval=None,
    concurrency=10,
    max_active_runs=5,
)

download_dataset = LocalDoccanoDownloadDatasetOperator(dag=dag)
unzip_files = ZipUnzipOperator(
    dag=dag, input_operator=download_dataset, mode="unzip", batch_level=True
)

doccano_tags = ProcessStudyIdsOperator(dag=dag, input_operator=unzip_files)

tag_dataset = LocalTaggingOperator(
    dag=dag,
    input_operator=doccano_tags,
    add_tags_from_file=True,
    tags_to_add_from_file=["doccano_tags"],
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

download_dataset >> unzip_files >> doccano_tags >> tag_dataset >> clean
