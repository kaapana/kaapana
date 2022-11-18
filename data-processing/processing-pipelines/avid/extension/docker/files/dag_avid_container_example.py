from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.AVIDBaseOperator import AVIDBaseOperator
from kaapana.operators.KaapanaBaseOperator import default_registry

from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from avid.actions.MitkFileConverter import MitkFileConverterBatchAction

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
    dag_id='demo-avid-container-example',
    default_args=args,
    schedule_interval=None,
    concurrency=30,
    max_active_runs=15
)

get_input = LocalGetInputDataOperator(dag=dag)
avid = AVIDBaseOperator(dag=dag, input_operator=get_input, name='avid-convert',
                        batch_action_class = MitkFileConverterBatchAction,
                        input_alias='inputSelector',
                        image=f"{default_registry}/mitk-fileconverter:2021-02-18-python",
                        image_pull_secrets=["registry-secret"],
                        envs = {
                            "CONVERTTO":'nrrd',
                            "THREADS":'3'
                        })
put_statistcs_to_minio = LocalMinioOperator(dag=dag, action='put', task_id="minio-put-statistics", zip_files=True,
                                            action_operators=[avid],
                                            file_white_tuples=('.png','.csv', '.zip'))

clean = LocalWorkflowCleanerOperator(dag=dag)

get_input >> avid >> put_statistcs_to_minio #>> clean