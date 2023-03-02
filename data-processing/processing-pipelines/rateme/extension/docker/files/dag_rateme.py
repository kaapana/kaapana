from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.KaapanaApplicationOperator import KaapanaApplicationOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION
from kaapana.operators.LocalTaggingOperator import LocalTaggingOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator


max_active_runs = 5

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": True,
                "required": True
            },
            "annotator": {
                "title": "User ID",
                "descritption": "Set user ID",
                "type": "string",
                "readOnly": False,
                "required": False
            },
            "input": {
                "title": "Input Modality",
                "default": "XR",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
                "required": False
            }
        }
    }
}

args = {
    'ui_visible': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='rateme',
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

rateme = KaapanaApplicationOperator(
    dag=dag,
    name="rateme",
    input_operator=get_input,
    chart_name='rateme-chart',
    version=KAAPANA_BUILD_VERSION,
)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True
    )

put_to_minio = LocalMinioOperator(
    dag=dag,
    action='put',
    action_operators=[rateme],
    bucket_name="rateme",
    zip_files=True)


get_input >> rateme >> put_to_minio >> clean