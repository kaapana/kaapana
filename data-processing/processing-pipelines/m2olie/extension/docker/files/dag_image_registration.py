from datetime import datetime, timedelta

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from airflow.utils.dates import days_ago
from airflow.models import DAG
from airflow.operators.dummy_operator import DummyOperator
from m2olie.LocalCallbackfunction import LocalCallbackfunction
from m2olie.LocalGetAdditionalInput import LocalGetAdditionalInput
from m2olie.LocalCreateMITKScene import LocalCreateMITKScene
from m2olie.ElastixRegistration import ElastixRegistration
from m2olie.NiftiConvOperator import NiftiConvOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator


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
input_converted = DcmConverterOperator(dag=dag, input_operator=get_input)
get_input_moving = LocalGetAdditionalInput(dag=dag)
input_moving_converted = DcmConverterOperator(
    dag=dag, name="dcm-converter_moving", input_operator=get_input_moving
)
registration = ElastixRegistration(
    dag=dag,
    task_id="registration",
    operator_in_dir_fixed=input_converted.operator_out_dir,
    operator_in_dir_moving=input_moving_converted.operator_out_dir,
)
create_mitk_scene = LocalCreateMITKScene(
    dag=dag,
    additional_input=input_moving_converted.operator_out_dir,
    registration_dir=registration.operator_out_dir,
    input_operator=input_converted,
)
launch_app = KaapanaApplicationOperator(
    dag=dag,
    name="application-registration-flow",
    input_operator=create_mitk_scene,
    chart_name="m2olie-workbench-chart",
    version=KAAPANA_BUILD_VERSION,
)
m2olie_callback_funktion = LocalCallbackfunction(dag=dag, input_operator=get_input)
convert_nifti = NiftiConvOperator(dag=dag, input_operator=registration)
dcm_send_result = DcmSendOperator(
    dag=dag,
    input_operator=convert_nifti,
    ae_title="REGISTRATION",
    pacs_host="x.x.x.x",
    pacs_port="11112",
    enable_proxy=True,
    no_proxy=".svc,.svc.cluster,.svc.cluster.local",
)
dcm_send_result_local_pacs = DcmSendOperator(
    dag=dag, name="local-dcm-send", input_operator=convert_nifti
)


clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

(
    get_input
    >> input_converted
    >> get_input_moving
    >> input_moving_converted
    >> registration
    >> create_mitk_scene
    >> launch_app
    >> convert_nifti
    >> dcm_send_result
    >> clean
)
convert_nifti >> dcm_send_result_local_pacs >> clean
registration >> m2olie_callback_funktion >> clean
