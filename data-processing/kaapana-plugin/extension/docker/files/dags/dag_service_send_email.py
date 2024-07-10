from kaapana.operators.LocalEmailSendOperator import LocalEmailSendOperator

from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.blueprints.kaapana_global_variables import (
    SMTP_HOST,
    SMTP_PORT,
    EMAIL_ADDRESS_SENDER,
    SMTP_USERNAME,
    SMTP_PASSWORD,
)

log = LoggingMixin().log
smtp_host = SMTP_HOST
smtp_port = SMTP_PORT
sender = EMAIL_ADDRESS_SENDER
smtp_username = SMTP_USERNAME
smtp_password = SMTP_PASSWORD
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
                "description": "Email addresses of  receivers.",
                "type": "array",
                "items": {"type": "string"},
                "required": True,
                # "default": receivers,
            },
            "sender": {
                "title": "Sender",
                "description": "Specify the url/IP of the DICOM receiver.",
                "type": "string",
                "default": sender,
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
                "defualt": smtp_username,
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
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="service-email-send",
    default_args=args,
    concurrency=50,
    max_active_runs=50,
    schedule_interval=None,
    tags=["service"],
)

local_email_send = LocalEmailSendOperator(
    dag=dag,
    send_email=True,
    smtp_host=smtp_host,
    smtp_port=smtp_port,
    smtp_username=smtp_username,
    smtp_password=smtp_password,
    sender=sender,
)