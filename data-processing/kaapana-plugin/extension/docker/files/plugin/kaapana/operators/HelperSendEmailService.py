from airflow.api.common.trigger_dag import trigger_dag as trigger
from kaapana.blueprints.kaapana_utils import generate_run_id
from typing import Optional, List
import requests
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
import logging
import re


logger = logging.getLogger(__name__)


BACKEND_API = f"http://kaapana-backend-service.{SERVICES_NAMESPACE}.svc:5000"
"""
    Helper to trigger an email send 
    (only one email per workflow execution, independent of the number of jobs)

    Example usage on failure:
    1.Make sure a valid smtp_host and port are set in the deploy_platform script or
    in the dag_service_send_email.py otherwise no email will be send.
    2. Make sure the username is a valid email or hardcode a receiver in service-send-email
    3. add "send_email_on_workflow_failure" to the default_args:
    args = {
        "send_email_on_workflow_failure": True,
    }


    OR:
    Alternatively, this helper functions are used in the  dag_service_send_email dag.
    By manually triggering the workflow via the ui form and specifying the desired monitored workflow_name,
    an email will be send, when all dag runs of this workflow will have finished
"""


def trigger_email_workflow(
    workflow_name_monitor: str,
    receivers: Optional[List[str]] = None,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    sender: Optional[str] = None,
    smtp_username: Optional[str] = None,
    smtp_password: Optional[str] = None,
    trigger_run_id: str = None,
):
    """
    Triggers an email send workflow by setting up the email configuration and initiating the 'service-email-send' DAG.

    Args:
        workflow_name_monitor (str): Name of the workflow to monitor.
        receivers (List[str]): List of email receivers.
        smtp_host (Optional[str]): SMTP host for email sending.
        smtp_port (Optional[int]): SMTP port number.
        sender (Optional[str]): Email address of the sender.
        smtp_username (Optional[str]): SMTP username for authentication.
        smtp_password (Optional[str]): SMTP password for authentication.
        trigger_run_id (str): Optional ID to trigger an email only on failure.

    Returns:
        None
    """
    dag_run_id = generate_run_id("service-email-send")

    # Build the workflow_form dict conditionally
    workflow_form = {
        "workflow_name_monitor": workflow_name_monitor,
    }

    if receivers is not None:
        workflow_form["receivers"] = receivers
    if sender is not None:
        workflow_form["sender"] = sender
    if smtp_host is not None:
        workflow_form["smtp_host"] = smtp_host
    if smtp_port is not None:
        workflow_form["smtp_port"] = smtp_port
    if smtp_username is not None:
        workflow_form["smtp_username"] = smtp_username
    if smtp_password is not None:
        workflow_form["smtp_password"] = smtp_password
    if trigger_run_id is not None:
        workflow_form["trigger_run_id"] = trigger_run_id

    conf_data = {
        "data_form": {
            "workflow_form": workflow_form,
        }
    }
    trigger(
        dag_id="service-email-send",
        run_id=dag_run_id,
        conf=conf_data,
        replace_microseconds=False,
    )


def extract_workflow_form(conf):
    """
    Extracts the 'workflow_form' from the provided configuration.

    Args:
        conf (dict): Configuration dictionary containing workflow and email data.

    Returns:
        dict: Extracted workflow form data.

    Raises:
        Exception: If the 'workflow_form' is not found.
    """
    print(conf)
    data_form = conf.get("data_form", None)
    workflow_form = None
    if data_form:
        workflow_form = data_form.get("workflow_form", None)
    if not workflow_form:
        workflow_form = conf.get("workflow_form", None)
        if not workflow_form:
            raise Exception("ERROR: workflow_form is not defined")
    return workflow_form


def handle_task_failure_alert(context):
    """
    Handles task failure alert by checking the workflow and sending failure email if necessary.

    Args:
        context (dict): Context of the failed task, containing run ID and DAG run info.

    Returns:
        None
    """
    logger.info("A task has failed")
    run_id = context["run_id"]
    conf = context["dag_run"].conf
    workflow_form = extract_workflow_form(conf)
    workflow_name = workflow_form.get("workflow_name", None)
    if workflow_name is None:
        raise Exception("ERROR: workflow_name is not defined")

    send_email = workflow_form.get("send_email", False)
    if send_email:
        logger.info(
            "Not triggering send-mail DAG, as an email will be sent with the results."
        )
        return

    if not check_email_required(workflow_name, run_id):
        logger.info("Not triggering send-mail DAG, as it was already triggered.")
        return

    receivers = None
    username = workflow_form.get("username", None)
    if username:
        # Basic regex pattern for email validation
        pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
        if bool(re.match(pattern, username)):
            receivers = [username]

    logger.info("Triggering service-email-send")
    trigger_email_workflow(
        workflow_name_monitor=workflow_name,
        receivers=receivers,
        trigger_run_id=run_id,
    )


def fetch_task_list(workflow_name):
    """
    Fetches the list of tasks for a given workflow name by querying the backend API.

    Args:
        workflow_name (str): Name of the workflow.

    Returns:
        list: List of tasks related to the workflow.

    Raises:
        Exception: If the API response returns a non-200 status code.
    """
    url = f"{BACKEND_API}/client/jobs"
    res = requests.get(url, params={"workflow_name": workflow_name})
    if res.status_code != 200:
        raise Exception(f"ERROR: [{res.status_code}] {res.text}")
    task_list = res.json()
    return task_list


def check_email_required(calling_workflow: str, calling_run_id: str):
    """
    Determines if sending an email is required based on task failures and the smallest run ID.

    Args:
        calling_workflow (str): Name of the workflow calling the check.
        calling_run_id (str): Run ID of the current workflow.

    Returns:
        bool: True if an email should be sent, False otherwise.
    """
    logger.info(f"Calling run ID: {calling_run_id}")
    logger.info(f"Calling workflow: {calling_workflow}")

    task_list = fetch_task_list(calling_workflow)
    keys_to_select = ["status"]

    task_list_filtered = [
        {
            key: value
            for key, value in entry.items()
            if key in keys_to_select and value == "failed"
        }
        for entry in task_list
    ]

    if not task_list_filtered:
        logger.info("No task has failed!")
        return False

    min_id_dag_run = min(task_list, key=lambda x: x["id"])
    if min_id_dag_run["run_id"] != calling_run_id:
        logger.info(
            f"Another task with a failed status exists. Current run ID: {calling_run_id},"
            f" smallest failed task run ID: {min_id_dag_run['run_id']}"
        )
        return False
    else:
        return True
