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

args = {
    "ui_visible": False,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="vnc-spe-pod-orchestrator",
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
trusted_post_etl = TrustedPostETLOperator(dag=dag)
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
    >> trusted_post_etl
)
trusted_post_etl >> watcher
trusted_post_etl >> delete_iso_inst >> clean
