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
from tfda_spe_orchestrator.FetchResultsOperator import FetchResultsOperator
from tfda_spe_orchestrator.TrustedPostETLOperator import TrustedPostETLOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.KaapanaApplicationOperator import KaapanaApplicationOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.HelperMinio import HelperMinio
from kaapana.blueprints.kaapana_global_variables import KAAPANA_BUILD_VERSION

buckets = HelperMinio.minioClient.list_buckets()
bucket_names = [bucket.name for bucket in buckets]

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "bucket_name": {
                "title": "Select Data to process",
                "description": "It should be the name of a Bucket from MinIO store",
                "type": "string",
                "enum": list(set(bucket_names)),
                "readOnly": False,
            },
            "container_registry_url": {
                "title": "Enter container registry URL",
                "type": "string",
                "default": "registry.hub.docker.com/kaushap",
                "required": True,
            },
            "container_registry_user": {
                "title": "Enter container registry username (optional)",
                "description": "Enter only if downloading your container needs login",
                "type": "string",
            },
            "container_registry_pwd": {
                "title": "Enter container registry password (optional)",
                "description": "Enter only if downloading your container needs login",
                "type": "string",
                "x-props": {"type": "password"},
                "readOnly": False,
            },
            "container_name_version": {
                "title": "Enter container name:version",
                "type": "string",
                "default": "testdock:latest",
                "required": True,
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
    dag_id="vnc-spe-vm-orchestrator",
    default_args=args,
    concurrency=10,
    max_active_runs=10,
    schedule_interval=None,
)

load_platform_config = LocalLoadPlatformConfigOperator(
    dag=dag, platform_config_file="platform_config.json"
)
create_iso_env = ManageIsoInstanceOperator(
    dag=dag, instanceState="present", taskName="create-iso-inst"
)
setup_vnc_server = SetupVNCServerOperator(dag=dag)
trusted_pre_etl = TrustedPreETLOperator(dag=dag)
get_input = LocalGetInputDataOperator(dag=dag)
get_minio_bucket = LocalMinioOperator(
    action="get",
    dag=dag,
    name="get-data-bucket",
    local_root_dir="{run_dir}/user-selected-data",
    operator_out_dir="user-selected-data",
)
copy_data_algo = CopyDataAndAlgoOperator(dag=dag, input_operator=get_minio_bucket)
spe_vnc_client = KaapanaApplicationOperator(
    dag=dag,
    name="spe-novnc-client",
    input_operator=get_input,
    chart_name="spe-novnc-client-chart",
    version=KAAPANA_BUILD_VERSION,
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
watcher = DummyOperator(task_id="watcher", dag=dag, trigger_rule="all_success")
(
    load_platform_config
    >> create_iso_env
    >> setup_vnc_server
    >> trusted_pre_etl
    >> get_input
    >> get_minio_bucket
    >> copy_data_algo
    >> spe_vnc_client
    >> trusted_post_etl
    >> fetch_results
    >> upload_results
)
trusted_post_etl >> watcher
trusted_post_etl >> delete_iso_inst >> clean
