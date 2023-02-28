from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from tfda_execution_orchestrator.LocalManageIsoInstanceOperator import LocalManageIsoInstanceOperator
from tfda_execution_orchestrator.LocalInstallPlatformDepsOnIsoEnvOperator import LocalInstallPlatformDepsOnIsoEnvOperator
from tfda_execution_orchestrator.LocalDeployPlatformOnIsoEnvOperator import LocalDeployPlatformOnIsoEnvOperator
from tfda_execution_orchestrator.LocalTrustedPreETLOperator import LocalTrustedPreETLOperator
from tfda_execution_orchestrator.LocalCopyDataAndAlgoOperator import LocalCopyDataAndAlgoOperator
from tfda_execution_orchestrator.LocalRunAlgoOperator import LocalRunAlgoOperator
from tfda_execution_orchestrator.LocalTFDAPrepareEnvOperator import LocalTFDAPrepareEnvOperator
from tfda_execution_orchestrator.LocalFetchResultsOperator import LocalFetchResultsOperator
from tfda_execution_orchestrator.LocalTrustedPostETLOperator import LocalTrustedPostETLOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from airflow.operators.python_operator import PythonOperator

log = LoggingMixin().log

ae_title = "NONE"
pacs_host = ""
pacs_port = 11112

args = {
    "ui_visible": True,
    # 'ui_forms': ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="dag-tfda-execution-orchestrator",
    default_args=args,
    concurrency=10,
    max_active_runs=10,
    schedule_interval=None,
)

create_iso_env = LocalManageIsoInstanceOperator(dag=dag, instanceState="present", taskName="create-iso-inst")
prepare_env = LocalTFDAPrepareEnvOperator(dag=dag)
trusted_pre_etl = LocalTrustedPreETLOperator(dag=dag)
copy_data_algo = LocalCopyDataAndAlgoOperator(dag=dag)
run_isolated_workflow = LocalRunAlgoOperator(dag=dag)
fetch_results = LocalFetchResultsOperator(dag=dag)
trusted_post_etl = LocalTrustedPostETLOperator(dag=dag)
delete_iso_inst = LocalManageIsoInstanceOperator(dag=dag, trigger_rule="all_done", instanceState="absent", taskName="delete-iso-inst")
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True, trigger_rule="all_done")

def final_status(**kwargs):
    for task_instance in kwargs['dag_run'].get_task_instances():
        if task_instance.current_state() != "success" and \
                task_instance.task_id != kwargs['task_instance'].task_id:
            raise Exception(f"Task {task_instance.task_id} failed! Failing this DAG run...")

final_status = PythonOperator(
    task_id='final_status',
    provide_context=True,
    python_callable=final_status,
    trigger_rule="all_done", # Ensures this task runs even if upstream fails
    dag=dag,
)

create_iso_env >> prepare_env >> trusted_pre_etl >> copy_data_algo >> run_isolated_workflow >> fetch_results >> trusted_post_etl >> delete_iso_inst >> clean >> final_status
