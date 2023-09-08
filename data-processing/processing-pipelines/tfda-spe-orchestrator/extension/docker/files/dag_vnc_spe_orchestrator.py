from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from tfda_spe_orchestrator.LocalLoadPlatformConfigOperator import (
    LocalLoadPlatformConfigOperator,
)
from tfda_spe_orchestrator.ManageIsoInstanceOperator import (
    ManageIsoInstanceOperator,
)
from tfda_spe_orchestrator.TrustedPreETLOperator import TrustedPreETLOperator
from tfda_spe_orchestrator.CopyDataAndAlgoOperator import CopyDataAndAlgoOperator
from tfda_spe_orchestrator.RunAlgoOperator import RunAlgoOperator
from tfda_spe_orchestrator.FetchResultsOperator import FetchResultsOperator
from tfda_spe_orchestrator.TrustedPostETLOperator import TrustedPostETLOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator

args = {
    "ui_visible": False,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="vnc-spe-orchestrator",
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
trusted_pre_etl = TrustedPreETLOperator(dag=dag)
get_minio_bucket = LocalMinioOperator(
    action="get",
    dag=dag,
    name="get-data-bucket",
    local_root_dir="{run_dir}/user-selected-data",
    operator_out_dir="user-selected-data",
)
copy_data_algo = CopyDataAndAlgoOperator(dag=dag, input_operator=get_minio_bucket)
run_isolated_workflow = RunAlgoOperator(dag=dag)
fetch_results = FetchResultsOperator(dag=dag, operator_out_dir="results")
trusted_post_etl = TrustedPostETLOperator(dag=dag)
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
    dag=dag, clean_workflow_dir=True, trigger_rule="all_success"
)
(
    load_platform_config
    >> create_iso_env
    >> trusted_pre_etl
    >> get_minio_bucket
    >> copy_data_algo
    >> run_isolated_workflow
    >> fetch_results
    >> trusted_post_etl
    >> upload_results
    >> delete_iso_inst
    >> clean
)
