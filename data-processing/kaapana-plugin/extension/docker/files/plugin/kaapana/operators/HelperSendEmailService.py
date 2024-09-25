from airflow.api.common.trigger_dag import trigger_dag as trigger
from kaapana.blueprints.kaapana_utils import generate_run_id
from typing import Optional, List
import requests
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
import logging
import re


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

BACKEND_API = f"http://kaapana-backend-service.{SERVICES_NAMESPACE}.svc:5000"
"""
    Helper to trigger an email send.

    Example usage on failure:
    # make sure a valid smtp_host and port are set in the deploy_platform script or
    # in the dag_service_send_email.py otherwise no email will be send.
    add "send_email_on_workflow_failure" to the default_args:
    args = {
        "send_email_on_workflow_failure": True,
    }

    # Alternatively, this is used in the required dag_service_send_email dag.
    By manally triggering the workflow via the ui form and specifying the desired monitored workflow_name,
    an email will be send, when all dag runs of this workflow will have finished.
    ```
"""


class HelperSendEmailService:
    @staticmethod
    def trigger(
        workflow_name_monitor: str,
        receivers: List[str] = [""],
        smtp_host: str = None,
        smtp_port: int = 0,
        sender: Optional[str] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        trigger_run_id: str = None,
    ):
        # Set up email configuration
        dag_run_id = generate_run_id("service-email-send")
        conf_data = {
            "data_form": {
                "workflow_form": {
                    "workflow_name_monitor": workflow_name_monitor,
                    "receivers": receivers,
                    "sender": sender,
                    "smtp_host": smtp_host,
                    "smtp_port": smtp_port,
                    "smtp_username": smtp_username,
                    "smtp_password": smtp_password,
                    "trigger_run_id": trigger_run_id,  # set this, if triggered on failure only
                },
            }
        }
        trigger(
            dag_id="service-email-send",
            run_id=dag_run_id,
            conf=conf_data,
            replace_microseconds=False,
        )

    @staticmethod
    def get_workflow_form(conf):
        data_form = conf.get("data_form", None)
        workflow_form = None
        if data_form:
            workflow_form = data_form.get("workflow_form", None)
        if not workflow_form:
            workflow_form = conf.get("workflow_form", None)
            if not workflow_form:
                raise Exception(f"ERROR: workflow_form is not defined")
        return workflow_form

    @staticmethod
    def task_failure_alert(context):
        logger.info("A task has failed")
        run_id = context["run_id"]
        conf = context["dag_run"].conf
        workflow_form = HelperSendEmailService.get_workflow_form(conf)
        workflow_name = workflow_form.get("workflow_name", None)
        if workflow_name is None:
            raise Exception(f"ERROR: workflow_name is not defined")
        send_email = workflow_form.get("send_email", False)
        if send_email:
            logger.info(
                "Not Triggering send-mail dag, since an email with the results will be send anyway."
            )
            return
        if not HelperSendEmailService.send_requiered(workflow_name, run_id):
            logger.info("Not Triggering send-mail dag, since already triggered.")
            return
        receivers = None
        username = workflow_form.get("username", None)
        if username:
            # Basic regex pattern for email validation, just basic
            pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
            if bool(re.match(pattern, username)):
                receivers = [username]
        logger.info("Trigger service-email-send")
        HelperSendEmailService.trigger(
            workflow_name_monitor=workflow_name,
            receivers=receivers,
            trigger_run_id=run_id,
        )

    @staticmethod
    def get_task_list(workflow_name):
        url = f"{BACKEND_API}/client/jobs"
        res = requests.get(url, params={"workflow_name": workflow_name})
        if res.status_code != 200:
            raise Exception(f"ERROR: [{res.status_code}] {res.text}")
        task_list = res.json()
        return task_list

    @staticmethod
    def send_requiered(calling_workflow: str, calling_run_id: str):
        logger.info(f"Calling run id: {calling_run_id}")
        logger.info(f"Calling calling_workflow: {calling_workflow}")
        task_list = HelperSendEmailService.get_task_list(calling_workflow)
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
            logger.info("No task has status failed!")
            return False

        min_id_dag_run = min(task_list, key=lambda x: x["id"])
        # only send email for one task-> only if this has the smallest id
        if min_id_dag_run["run_id"] != calling_run_id:
            logger.info(
                f"Other task with status failed exists. Run id of this task-run is {calling_run_id} and the to trigger sending run-id is {min_id_dag_run['run_id']}"
            )
            return False
        else:
            return True
