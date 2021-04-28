from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from bodypartregression import BprOperator

max_active_runs = 10
ui_forms = {}
args = {
    'ui_visible': True,
    'ui_dag_info': all_selectable_tasks,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='bodypartregression',
    default_args=args,
    concurrency=10,
    max_active_runs=max_active_runs,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(
    dag=dag,
    parallel_downloads=5,
    check_modality=True
)

dcm2nifti = DcmConverterOperator(
    dag=dag,
    input_operator=get_input,
    output_format='nii.gz'
)

bodypartregression = BprOperator(
    dag=dag,
    input_operator=dcm2nifti
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=False)

get_input >> dcm2nifti >> bodypartregression >> clean
