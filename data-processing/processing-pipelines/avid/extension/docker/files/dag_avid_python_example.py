from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.AVIDPythonOperator import AVIDPythonOperator

from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "input": {
                "title": "Input",
                "default": "SEG",
                "description": "Input-data modality",
                "type": "string",
                "readOnly": True,
            },
        }
    }
}

args = {
    'ui_visible': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 1,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='demo-avid-python-example',
    default_args=args,
    schedule_interval=None,
    concurrency=30,
    max_active_runs=15
)


def my_function(outputs, **kwargs):
    with open(outputs[0], "w") as ofile:
         ofile.write(str(kwargs))


get_input = LocalGetInputDataOperator(dag=dag)
avid = AVIDPythonOperator(dag=dag, input_operator=get_input, python_callable=my_function, name='avid_py_op',output_default_extension='txt')
put_statistcs_to_minio = LocalMinioOperator(dag=dag, action='put', task_id="minio-put-statistics", zip_files=True,
                                            action_operators=[avid],
                                            file_white_tuples=('.png','.csv', '.zip'))

clean = LocalWorkflowCleanerOperator(dag=dag)

get_input >> avid >> put_statistcs_to_minio >> clean