from datetime import timedelta
import time
import smtplib
from email.message import EmailMessage
from airflow.utils.state import State
from tabulate import tabulate
from typing import Optional, List
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators import HelperSendEmailService
import re
import logging

logger = logging.getLogger(__name__)


class LocalEmailSendOperator(KaapanaPythonBaseOperator):
    """
    (1)
    Operator designed for use in DAGs to facilitate email notifications.
    This operator, when added to a DAG, is responsible for triggering a single email notification encompassing all DAG runs within a workflow trigger (Jobs).

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
    AND
    add LocalEmailSendOperator to the dag (with send_email=True to always send an email,
    False, only if ui parameter added and ui form parameter is send_email=True):
    e.g.:
    from kaapana.operators.LocalEmailSendOperator import LocalEmailSendOperator
    local_email_send = LocalEmailSendOperator(dag=dag, send_email=False)




    (2)
    Optionally an operator falure can be configured with the "send_email_on_workflow_failure" parameter to leverage the HelperSendEmailService task_failure_alert function.
    In such cases, the operator does not need to be explicitly added to the DAG; the email will be sent only on failure.

    (3)
    The dag (dag_id="service-email-send") can be directly triggered with valid "workflow_name" to notify a user when all Jobs of the workflow execution are done.
    """

    def get_input_value(self, workflow_form: dict, key: str):
        """Gets the input value from workflow_form or operator attributes."""
        return workflow_form.get(key, getattr(self, key, None))

    def filter_task_list(self, task_list: list):
        """Filter tasks to include specific keys in the email."""
        # Logic to filter the task list
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
            return []
        return task_list_filtered

    def append_workflow_details(self, task_list: list):
        """Append additional workflow details to the task list for email content."""
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

    def send_email_notification(self, task_list: list, workflow_name: str):
        """
        Sends an email notification with workflow results.

        Args:
            task_list (list): List of tasks with their details to be included in the email.
            workflow_name (str): The name of the workflow for which the email is being sent.

        Raises:
            Exception: If no valid receivers or SMTP configuration is provided.
        """
        workflow_form = HelperSendEmailService.extract_workflow_form(self.conf)
        receivers = self.get_input_value(workflow_form, "receivers")

        if not receivers or (
            isinstance(receivers, list) and len(receivers) == 1 and receivers[0] == ""
        ):
            username = workflow_form.get("username", None)
            if not username:
                raise Exception("Cannot send email, no receivers defined!")
            # On some platforms users are always emails, so check that, if this can be used
            # Basic regex pattern for email validation, just basic
            pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
            if bool(re.match(pattern, username)):
                receivers = [username]
            else:
                raise Exception("Cannot send email, no receivers defined!")

        smtp_port = self.get_input_value(workflow_form, "smtp_port")
        if smtp_port:
            smtp_port = int(smtp_port)
        else:
            smtp_port = 0

        smtp_username = self.get_input_value(workflow_form, "smtp_username")
        smtp_password = self.get_input_value(workflow_form, "smtp_password")
        smtp_host = self.get_input_value(workflow_form, "smtp_host")
        sender = self.get_input_value(workflow_form, "sender")

        if not smtp_host:
            raise Exception("Cannot send email, no smtp server defined!")

        if not sender:
            logging.warning(
                "No sender set. Some SMTP servers will not send data without a sender. If the send fails, this could be the reason."
            )

        # Add workflow details for the email
        self.append_workflow_details(task_list)
        task_list_filtered = self.filter_task_list(task_list)

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
        logger.info("Server info")
        logger.info(f"SMTP_HOST: {smtp_host}")
        logger.info(f"SMTP_PORT: {smtp_port}")
        logger.info(f"SMTP_USERNAME: {smtp_username}")
        logger.info(f"SENDER: {sender}")
        logger.info(f"RECEIVERS: {receivers}")
        # logger.info("Email content:")
        # logger.info(f"{msg}")'

        try:
            # Connect to the SMTP server and send the email
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                if smtp_username and smtp_password:
                    server.login(smtp_username, smtp_password)

                server.send_message(msg)
                server.quit()
            logger.info("Successfully sent email")
        except smtplib.SMTPException as e:
            logging.info(e)
            logger.info("Error: unable to send email")
            exit(1)

    def monitor_workflow_and_send_email(
        self, workflow_form: dict, workflow_name_monitor: str
    ):
        """Monitor the specified workflow and send an email when it's complete."""
        # Logic to monitor workflow and send email
        while True:
            task_list = HelperSendEmailService.fetch_task_list(workflow_name_monitor)
            keys_to_select = ["status"]
            task_list_filtered = [
                {key: value for key, value in entry.items() if key in keys_to_select}
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
                    if not HelperSendEmailService.check_email_required(
                        calling_workflow=workflow_name_monitor,
                        calling_run_id=trigger_run_id,
                    ):
                        return  # exit without sending a mail
                self.send_email_notification(task_list, workflow_name_monitor)
                return  # All statuses meet the condition, exit the loop
            logger.info("Wating for all tasks to finish!")
            time.sleep(30)

    def handle_normal_dag_execution(
        self, workflow_form, workflow_name, run_id, task_instance
    ):
        """Handle non-monitoring DAG execution and send email if required."""
        # Logic to handle non-monitoring DAG execution
        task_list = HelperSendEmailService.fetch_task_list(workflow_name)

        min_id_task = min(task_list, key=lambda x: x["id"])
        # only send email for one task-> only if this has the smallest id
        if min_id_task["run_id"] != run_id:
            task_instance.set_state(State.SKIPPED)
            return f"Task {task_instance.task_id} with run_id {run_id} is set to SKIPPED state."

        receivers = self.get_input_value(workflow_form, "receivers")
        if not receivers:
            username = workflow_form.get("username", None)
            if username:
                # Basic regex pattern for email validation, just basic
                pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
                if bool(re.match(pattern, username)):
                    receivers = [username]
        smtp_host = self.get_input_value(workflow_form, "smtp_host")
        smtp_port = self.get_input_value(workflow_form, "smtp_port")
        smtp_username = self.get_input_value(workflow_form, "smtp_username")
        smtp_password = self.get_input_value(workflow_form, "smtp_password")
        sender = workflow_form.get("workflow_name_monitor", None)

        logger.info(f"Triggering workflow result email for workflow {workflow_name}")
        HelperSendEmailService.trigger_email_workflow(
            workflow_name_monitor=workflow_name,
            receivers=receivers,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            sender=sender,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
        )

    def start_operator(self, ds, **kwargs):
        """
        Starts the email sending process for a DAG.

        Args:
            ds: Date string (templated).
            **kwargs: Other context arguments provided by Airflow.

        Returns:
            str: Message indicating the email task status.
        """
        self.conf = kwargs["dag_run"].conf
        run_id = kwargs["run_id"]
        task_instance = kwargs["ti"]
        logger.info(kwargs["run_id"])
        logger.info(self.conf)

        workflow_form = HelperSendEmailService.extract_workflow_form(self.conf)
        send_email = workflow_form.get("send_email", None)
        if not (self.send_email or send_email):
            task_instance.set_state(State.SKIPPED)
            return f"Send email is not enabled. Task {task_instance.task_id} with run_id {run_id} is set to SKIPPED state."

        # Operator triggerd to monitor, in this case an email will be send
        # this operation is only called if the operator is called in send-email dag
        workflow_name_monitor = workflow_form.get("workflow_name_monitor", None)
        if workflow_name_monitor:
            self.monitor_workflow_and_send_email(workflow_form, workflow_name_monitor)
            return

        # Operator executed during other dag
        # check if this dag run triggers the send-email dag, or not.

        workflow_name = workflow_form.get("workflow_name", None)
        if workflow_name is None:
            raise Exception(f"ERROR: workflow_name is not defined")
        # This function is called, if operator is added to other dags, to trigger send-email dag
        self.handle_normal_dag_execution(
            workflow_form, workflow_name, run_id, task_instance
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
        sender: Optional[str] = None,
        receivers: Optional[List[str]] = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
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
            python_callable=self.start_operator,
            execution_timeout=execution_timeout,
            **kwargs,
        )
