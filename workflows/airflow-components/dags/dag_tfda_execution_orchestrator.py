from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.LocalCreateIsoInstanceOperator import LocalCreateIsoInstanceOperator
from kaapana.operators.LocalInstallPlatformOnIsoEnvOperator import LocalInstallPlatformOnIsoEnvOperator
from kaapana.operators.LocalCopyDataAndAlgoOperator import LocalCopyDataAndAlgoOperator
from kaapana.operators.LocalRunAlgoSendResultOperator import LocalRunAlgoSendResultOperator
from kaapana.operators.LocalDeleteIsoEnvOperator import LocalDeleteIsoEnvOperator
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
install_platform = LocalInstallPlatformOnIsoEnvOperator(dag=dag)
copy_data_algo = LocalCopyDataAndAlgoOperator(dag=dag)
run_algo_send_result = LocalRunAlgoSendResultOperator(dag=dag)
delete_iso_inst = LocalDeleteIsoEnvOperator(dag=dag)
# dcm_send = DcmSendOperator(
#     dag=dag,
#     input_operator=get_input,
#     ae_title=ae_title,
#     pacs_host=pacs_host,
#     pacs_port=pacs_port,
#     host_network=True,
#     level='element'
# )

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

create_iso_env >> install_platform >> copy_data_algo >> run_algo_send_result >> delete_iso_inst >> clean
