import os

from kaapana.operators.LocalEmailSendOperator import LocalEmailSendOperator

from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG

smtp_host = os.getenv("SMTP_HOST", None)
smtp_port = os.getenv("SMTP_PORT", 0)
sender = os.getenv("EMAIL_ADDRESS_SENDER", None)
smtp_username = os.getenv("SMTP_USERNAME", None)
smtp_password = os.getenv("SMTP_PASSWORD", None)

# receivers = []
ui_forms = {
    "data_form": {},
    "workflow_form": {
        "type": "object",
        "properties": {
            "workflow_name_monitor": {
                "title": "Name of the Workflow to monitor",
                "description": "Specify the workflow to monitor.",
                "type": "string",
                "required": True,
            },
            "receivers": {
                "title": "Receivers",
                "description": "Email addresses of receivers.",
                "type": "array",
                "items": {"type": "string"},
                "required": True,
            },
            "sender": {
                "title": "Sender",
                "description": "Specify the url/IP of the DICOM receiver.",
                "type": "string",
            },
            "smtp_host": {
                "title": "SMTP Host",
                "description": "Specify the smtp-host.",
                "type": "string",
                "default": smtp_host,
            },
            "smtp_port": {
                "title": "SMTP Port",
                "description": "Specify the smtp-port.",
                "type": "integer",
                "default": smtp_port,
            },
            "smtp_username": {
                "title": "SMTP Username",
                "description": "Specify the smtp username.",
                "type": "string",
            },
            "smtp_password": {
                "title": "SMTP Password",
                "description": "Specify the smtp password.",
                "type": "string",
            },
        },
    },
}

args = {
    "ui_forms": ui_forms,
    "ui_visible": False,  # default not visible, to only trigger via other dags
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="service-email-send",
    default_args=args,
    concurrency=25,
    max_active_runs=25,
    schedule_interval=None,
    tags=["service"],
)

local_email_send = LocalEmailSendOperator(
    dag=dag,
    send_email=True,
    smtp_host=smtp_host,
    smtp_port=smtp_port,
    sender=sender,
    smtp_username=smtp_username,
    smtp_password=smtp_password,
)
