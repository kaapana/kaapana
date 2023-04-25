import random
from datetime import datetime, timedelta

from airflow.utils.dates import days_ago
from airflow.models import DAG
from airflow.models import Variable

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from federated_setup_node_test.LocalFedartedSetupFederatedTestOperator import LocalFedartedSetupFederatedTestOperator
from federated_setup_node_test.LocalFederatedSetupFromPreviousTestOperator import LocalFederatedSetupFromPreviousTestOperator
from federated_setup_node_test.LocalFederatedSetupSkipTestOperator import LocalFederatedSetupSkipTestOperator

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "task": {
                "title": "Test federated setup",
                "description": "This is just a test",
                "type": "string",
                "default": "Test",
                "required": True
            },
            "simulate_fail_round": {
                "type": "integer",
                "title": "Simulate Fail",
                "description": "In which round simulating a fail (starting from 0)"
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
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='federated-setup-node-test',
    default_args=args,
    concurrency=4,
    max_active_runs=4,
    schedule_interval=None
)

federated_setup_from_previous_test = LocalFederatedSetupFromPreviousTestOperator(dag=dag)
federated_setup_federated_test = LocalFedartedSetupFederatedTestOperator(dag=dag, input_operator=federated_setup_from_previous_test)
federated_setup_skip_test = LocalFederatedSetupSkipTestOperator(dag=dag)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

federated_setup_from_previous_test >> federated_setup_federated_test >> federated_setup_skip_test >> clean