from datetime import timedelta
import time
import smtplib
from email.message import EmailMessage
from airflow.utils.state import State
from tabulate import tabulate
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperSendEmailService import HelperSendEmailService
import re
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


class LocalEmailSendOperator(KaapanaPythonBaseOperator):
    """
    Operator designed for use in DAGs to facilitate email notifications.

    This operator, when added to a DAG, is responsible for triggering a single email notification encompassing all DAG runs within a workflow trigger.
    Optionally, it can be configured with the "on_failure_callback" parameter to leverage the HelperSendEmailService task_failure_alert function. In such cases, the operator does not need to be explicitly added to the DAG; the email will be sent only on failure.

    Example usage in dag, add operator and ui forms paramenter:
    "send_email": {
        "title": "Send workflow result email",
        "description": "Sends a result email to the user.",
        "type": "boolean",
        "default": True,
        "readOnly": False,
    },
    "receivers": {
        "title": "Receivers",
        "description": "Email addresses of receivers.",
        "type": "array",
        "items": {    "type": "string" },
        "required": False,
    }
    # if no receivers are set and send_email is selcted the email will be send to the "username" email, if it is an email-address.
    AND add this to the dag (with send_email=True to always send an email, False, only if paramet send_email=True):

    local_email_send = LocalEmailSendOperator(dag=dag, send_email=False)
    """

    def sending_email(self, task_list, workflow_name):
        receivers = None
        if self.receivers:
            receivers = self.receivers
        workflow_form = HelperSendEmailService.get_workflow_form(self.conf)
        _receivers = workflow_form.get("receivers", None)
        if _receivers:
            receivers = _receivers
        if not receivers or (
            isinstance(receivers, list) and len(receivers) == 1 and receivers[0] == ""
        ):
            username = workflow_form.get("username", None)
            if username:
                # On some platforms users are always emails, so check that, if this can be used
                # Basic regex pattern for email validation, just basic
                pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
                if bool(re.match(pattern, username)):
                    receivers = [username]
            else:
                raise Exception("Cannot send email, no receivers defined!")

        smtp_port = 0
        if self.smtp_port:
            smtp_port = int(self.smtp_port)
        port = workflow_form.get("smtp_port", None)
        if port:
            smtp_port = int(port)

        smtp_username = None
        if self.smtp_username:
            smtp_username = self.smtp_username
        username = workflow_form.get("smtp_username", None)
        if username:
            smtp_username = username

        smtp_password = None
        if self.smtp_password:
            smtp_password = self.smtp_password
        password = workflow_form.get("smtp_password", None)
        if password:
            smtp_password = password

        smtp_host = None
        if self.smtp_host:
            smtp_host = self.smtp_host
        server = workflow_form.get("smtp_host", None)
        if server:
            smtp_host = server
        if not smtp_host:
            raise Exception("Cannot send email, no smtp server defined!")

        sender = None
        if self.sender:
            sender = self.sender
        _sender = workflow_form.get("sender", None)
        if _sender:
            sender = _sender
        if not sender:
            logging.warning(
                "No sender set. Some SMTP servers will not send data without a sender. If the send fails, this could be the reason."
            )
        if "workflow_details" in self.keys_to_select:
            for entry in task_list:
                entry["workflow_details"] = ""
                if "kaapana_instance" in entry:
                    if (
                        "protocol" in entry["kaapana_instance"]
                        and "host" in entry["kaapana_instance"]
                    ):
                        protocol = entry["kaapana_instance"]["protocol"]
                        host = entry["kaapana_instance"]["host"]
                        url = f"{protocol}://{host}/flow/dags/"
                        if "dag_id" in entry and "run_id" in entry:
                            url += f"{entry['dag_id']}/grid?root=&dag_run_id={entry['run_id']}"
                            entry["workflow_details"] = url
        # Selected keys for the email:
        task_list_filtered = [
            {
                key: value
                for key, value in entry.items()
                if key in self.keys_to_select and value
            }
            for entry in task_list
        ]
        logger.info(task_list_filtered)
        # Check if there's any data to include in the table
        if not task_list_filtered:
            logger.info("No data available to include in the email.")
            return

        message_before_table = f"The following table contains the workflow result for workflow {workflow_name}:"
        table_html = tabulate(task_list_filtered, headers="keys", tablefmt="html")

        # Add custom styling to increase space between values in rows
        styled_table_html = table_html.replace("<td>", '<td style="padding: 0 15px;">')
        msg = EmailMessage()
        msg["Subject"] = "Workflow result"
        msg["From"] = sender
        msg["To"] = receivers
        msg.set_content(
            f"{message_before_table}\n\n{styled_table_html }", subtype="html"
        )
        # logger.info("Server info")
        # logger.info(f"SMTP_HOST: {smtp_host}")
        # logger.info(f"SMTP_PORT: {smtp_port}")
        # logger.info(f"SMTP_USERNAME: {smtp_username}")
        # logger.info(f"SENDER: {sender}")

        # logger.info("Email content:")
        # logger.info(f"{msg}")

        try:
            # Connect to the SMTP server and send the email
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                if smtp_username and smtp_password:
                    server.login(smtp_username, smtp_password)

                server.send_message(msg)
                server.quit()
            logger.info("Successfully sent email")
        except smtplib.SMTPException:
            logger.info("Error: unable to send email")
            exit(1)

    def start(self, ds, **kwargs):
        self.conf = kwargs["dag_run"].conf
        run_id = kwargs["run_id"]
        task_instance = kwargs["ti"]
        logger.info(kwargs["run_id"])
        logger.info(self.conf)

        workflow_form = HelperSendEmailService.get_workflow_form(self.conf)
        send_email = workflow_form.get("send_email", None)
        if not (self.send_email or send_email):
            task_instance.set_state(State.SKIPPED)
            return f"Send email is not enabled. Task {task_instance.task_id} with run_id {run_id} is set to SKIPPED state."

        # Operator triggerd to monitor, in this case an email will be send
        workflow_name_monitor = workflow_form.get("workflow_name_monitor", None)
        if workflow_name_monitor:
            while True:
                task_list = HelperSendEmailService.get_task_list(workflow_name_monitor)
                keys_to_select = ["status"]
                task_list_filtered = [
                    {
                        key: value
                        for key, value in entry.items()
                        if key in keys_to_select
                    }
                    for entry in task_list
                ]
                logger.info(task_list_filtered)

                # Check if all statuses are either 'success' or 'failed'
                if all(
                    entry["status"] in ["success", "failed", "skipped", "finished"]
                    for entry in task_list_filtered
                ):
                    trigger_run_id = workflow_form.get("trigger_run_id", None)
                    if trigger_run_id:
                        # trigger_run_id only set on failure, in rare cases a smaller run_id can fail after this send_required is triggered.
                        if not HelperSendEmailService.send_requiered(
                            calling_workflow=workflow_name_monitor,
                            calling_run_id=trigger_run_id,
                        ):
                            return  # exit without sending a mail
                    self.sending_email(task_list, workflow_name_monitor)
                    return  # All statuses meet the condition, exit the loop
                logger.info("Wating for all tasks to finish!")
                time.sleep(30)

        # Operator executed during other dag, check if this dag run triggers the send email dag, or not.
        workflow_name = workflow_form.get("workflow_name", None)
        if workflow_name is None:
            raise Exception(f"ERROR: workflow_name is not defined")
        task_list = HelperSendEmailService.get_task_list(workflow_name)

        min_id_task = min(task_list, key=lambda x: x["id"])
        # only send email for one task-> only if this has the smallest id
        if min_id_task["run_id"] != run_id:
            task_instance.set_state(State.SKIPPED)
            return f"Task {task_instance.task_id} with run_id {run_id} is set to SKIPPED state."

        receivers = workflow_form.get("receivers", None)
        if not receivers:
            username = workflow_form.get("username", None)
            if username:
                # Basic regex pattern for email validation, just basic
                pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
                if bool(re.match(pattern, username)):
                    receivers = [username]
        smtp_host = workflow_form.get("smtp_host", None)
        smtp_port = workflow_form.get("smtp_port", None)
        sender = workflow_form.get("workflow_name_monitor", None)
        smtp_username = workflow_form.get("smtp_username", None)
        smtp_password = workflow_form.get("smtp_password", None)

        logger.info(f"Triggering workflow result email for workflow {workflow_name}")
        HelperSendEmailService.trigger(
            workflow_name_monitor=workflow_name,
            receivers=receivers,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            sender=sender,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
        )

    def __init__(
        self,
        dag,
        send_email: bool,
        name: str = "send-email",
        keys_to_select=[
            "status",
            "dag_id",
            "run_id",
            "external_job_id",
            "owner_kaapana_instance_name",
        ],
        sender: str = "",
        receivers: list = [""],
        smtp_host: str = "",
        smtp_port: int = 0,
        smtp_username: str = None,
        smtp_password: str = None,
        trigger_rule="all_done",
        execution_timeout=timedelta(hours=24),
        **kwargs,
    ):

        self.send_email = send_email
        self.sender = sender
        self.receivers = receivers
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.keys_to_select = keys_to_select

        super().__init__(
            dag=dag,
            name=name,
            trigger_rule=trigger_rule,
            python_callable=self.start,
            execution_timeout=execution_timeout,
            **kwargs,
        )
