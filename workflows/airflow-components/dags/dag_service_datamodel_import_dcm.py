from datamodel.LocalDatamodelImportDcm import LocalDatamodelImportDcm
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

from airflow.utils.dates import days_ago
from airflow.models import DAG
from datetime import timedelta

args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 1,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='service-datamodel-import-dcm',
    default_args=args,
    schedule_interval=None,
    concurrency=50,
    max_active_runs=20,
    tags=['service']
)

get_input = LocalGetInputDataOperator(dag=dag)

datamodel_import_dcm = LocalDatamodelImportDcm(
    dag=dag,
    input_operator=get_input
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)


get_input >> datamodel_import_dcm  >>  clean
