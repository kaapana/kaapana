from datetime import datetime, timedelta

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from airflow.utils.dates import days_ago
from airflow.models import DAG
from airflow.operators.dummy_operator import DummyOperator
from m2olie.LocalCallbackfunction import LocalCallbackfunction
from m2olie.LocalGetAdditionalInput import LocalGetAdditionalInput
from m2olie.LocalCreateMITKScene import LocalCreateMITKScene
from m2olie.ElastixRegistration import ElastixRegistration


from kaapana.operators.KaapanaApplicationOperator import KaapanaApplicationOperator
from kaapana.blueprints.kaapana_global_variables import KAAPANA_BUILD_VERSION

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "task_label": {
                "title": "Task Label",
                "description": "The M2olie Prometheus task label",
                "type": "string",
                "readOnly": False,
            },
            "process_instance_label": {
                "title": "Process Instance Label",
                "description": "The M2olie Prometheus process instance label",
                "type": "string",
                "readOnly": False,
            },
            "callback_instance_ip": {
                "title": "Callback Instance IP",
                "description": "The M2olie Prometheus callback ip.",
                "type": "string",
                "readOnly": False,
            },
        },
    }
}

args = {
    "ui_visible": True,
    "ui_federated": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="image_registration",
    default_args=args,
    concurrency=10,
    max_active_runs=1,
    schedule_interval=None,
    tags=["m2olie"],
)

get_input = LocalGetInputDataOperator(dag=dag)
get_input_additional = LocalGetAdditionalInput(dag=dag)
registration = ElastixRegistration(
    dag=dag,
    task_id="registration",
    operator_in_dir_fixed=get_input.operator_out_dir,
    operator_in_dir_moving=get_input_additional.operator_out_dir,
)
create_mitk_scene = LocalCreateMITKScene(
    dag=dag,
    additional_input=get_input_additional.operator_out_dir,
    registration_dir=registration.operator_out_dir,
    input_operator=get_input,
)
launch_app = KaapanaApplicationOperator(
    dag=dag,
    name="application-registration-flow",
    input_operator=create_mitk_scene,
    chart_name="m2olie-workbench-chart",
    version=KAAPANA_BUILD_VERSION,
)
m2olie_callback_funktion = LocalCallbackfunction(dag=dag, input_operator=get_input)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

(
    get_input
    >> get_input_additional
    >> registration
    >> create_mitk_scene
    >> launch_app
    >> clean
)
registration >> m2olie_callback_funktion >> clean
