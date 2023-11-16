from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from airflow.operators.dummy_operator import DummyOperator
from tfda_spe_orchestrator.LocalLoadPlatformConfigOperator import (
    LocalLoadPlatformConfigOperator,
)
from tfda_spe_orchestrator.ManageIsoInstanceOperator import (
    ManageIsoInstanceOperator,
)
from tfda_spe_orchestrator.SetupVNCServerOperator import SetupVNCServerOperator
from tfda_spe_orchestrator.TrustedPreETLOperator import TrustedPreETLOperator
from tfda_spe_orchestrator.CopyDataAndAlgoOperator import CopyDataAndAlgoOperator
from tfda_spe_orchestrator.RunAlgoOperator import RunAlgoOperator
from tfda_spe_orchestrator.FetchResultsOperator import FetchResultsOperator
from tfda_spe_orchestrator.TrustedPostETLOperator import TrustedPostETLOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.HelperMinio import HelperMinio

buckets = HelperMinio.minioClient.list_buckets()
bucket_names = [bucket.name for bucket in buckets]

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "bucket_name": {
                "title": "Select bucket to fetch resutls into",
                "description": "It should be the name of a Bucket from MinIO store",
                "type": "string",
                "enum": list(set(bucket_names)),
                "readOnly": False,
            },
            "spe_ip": {
                "title": "Enter the IP address of the SPE to be deleted",
                "type": "string",
                "required": True
            },
        },
    },
}

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="vnc-delete-spe-vm",
    default_args=args,
    concurrency=10,
    max_active_runs=10,
    schedule_interval=None,
)

load_platform_config = LocalLoadPlatformConfigOperator(
    dag=dag, platform_config_file="platform_config.json"
)
trusted_post_etl = TrustedPostETLOperator(dag=dag)
fetch_results = FetchResultsOperator(dag=dag, operator_out_dir="results")
upload_results = LocalMinioOperator(
    action="put",
    dag=dag,
    name="upload-results",
    bucket_name="results",
    action_operators=[fetch_results],
    zip_files=False,
)
delete_iso_inst = ManageIsoInstanceOperator(
    dag=dag, trigger_rule="all_done", instanceState="absent", taskName="delete-iso-inst"
)
clean = LocalWorkflowCleanerOperator(
    dag=dag, clean_workflow_dir=True, trigger_rule="all_done"
)
# Following operator fails the DAG if any previous operator fails
watcher = DummyOperator(task_id='watcher', dag=dag, trigger_rule='all_success')
(
    load_platform_config
    >> trusted_post_etl
    >> fetch_results
    >> upload_results
)
trusted_post_etl >> delete_iso_inst >> clean
