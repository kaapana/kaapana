from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from tfda_execution_orchestrator.LocalCreateIsoInstanceOperator import LocalCreateIsoInstanceOperator
from tfda_execution_orchestrator.LocalChangeIsoInstHostnameOperator import LocalChangeIsoInstHostnameOperator
from tfda_execution_orchestrator.LocalInstallPlatformDepsOnIsoEnvOperator import LocalInstallPlatformDepsOnIsoEnvOperator
from tfda_execution_orchestrator.LocalDeployPlatformOnIsoEnvOperator import LocalDeployPlatformOnIsoEnvOperator
from tfda_execution_orchestrator.LocalCopyDataAndAlgoOperator import LocalCopyDataAndAlgoOperator
from tfda_execution_orchestrator.LocalRunAlgoSendResultOperator import LocalRunAlgoSendResultOperator
from tfda_execution_orchestrator.LocalDeleteIsoEnvOperator import LocalDeleteIsoEnvOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log

ae_title = "NONE"
pacs_host = ""
pacs_port = 11112

args = {
    'ui_visible': True,
    # 'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='tfda-execution-orchestrator',
    default_args=args,
    concurrency=10,
    max_active_runs=10,
    schedule_interval=None
)

create_iso_env = LocalCreateIsoInstanceOperator(dag=dag)
# change_hostname = LocalChangeIsoInstHostnameOperator(dag=dag)
install_platform_dependencies = LocalInstallPlatformDepsOnIsoEnvOperator(dag=dag)
deploy_platform = LocalDeployPlatformOnIsoEnvOperator(dag=dag)
copy_data_algo = LocalCopyDataAndAlgoOperator(dag=dag)
run_algo_send_result = LocalRunAlgoSendResultOperator(dag=dag)
delete_iso_inst = LocalDeleteIsoEnvOperator(dag=dag)


clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

delete_iso_inst >> create_iso_env >> install_platform_dependencies >> deploy_platform >> copy_data_algo >> run_algo_send_result >> clean
