from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "pacs_host": {
                "title": "Receiver host",
                "description": "Specify the url/IP of the DICOM receiver. If not specified will send to the platform itself.",
                "type": "string",
                "default": "",
            },
            "pacs_port": {
                "title": "Receiver port",
                "description": "Specify the port of the DICOM receiver.",
                "type": "integer",
                "default": 11112,
            },
            "calling_ae_title_scu": {
                "title": "Calling AE Title (SCU)",
                "description": "Specify the Local Calling AET. Kaapana interprets this as the dataset name.",
                "type": "string",
                "default": "",
            },
            "called_ae_title_scp": {
                "title": "Called AE Title (SCP)",
                "description": "Specify the Remote Called AET. Kaapana interprets this as the project name.",
                "type": "string",
                "default": "",
            },
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
                "readOnly": False,
            },
        },
    }
}

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="send-dicom",
    default_args=args,
    concurrency=10,
    max_active_runs=10,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag)

dcm_send = DcmSendOperator(
    dag=dag,
    input_operator=get_input,
    enable_proxy=True,
    no_proxy=".svc,.svc.cluster,.svc.cluster.local",
    labels={"network-access": "external-ips"},
    # dev_server="code-server",
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> dcm_send >> clean
