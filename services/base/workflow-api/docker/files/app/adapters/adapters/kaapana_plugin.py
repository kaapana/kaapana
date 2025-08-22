import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.adapters.base import WorkflowEngineAdapter
from app import schemas, crud
from app.models import LifecycleStatus
from app.adapters.config import settings


class KaapanaPluginAdapter(WorkflowEngineAdapter):
    """
    Airflow-specific adapter implementation for synchronous communication.
    This adapter handles submitting, monitoring, and canceling workflows
    via the Airflow API.
    """

    AIRFLOW_STATUS_MAPPER = {
        "queued": LifecycleStatus.SCHEDULED,
        "running": LifecycleStatus.RUNNING,
        "success": LifecycleStatus.COMPLETED,
        "failed": LifecycleStatus.ERROR,
        "up_for_retry": LifecycleStatus.RUNNING,
        "up_for_reschedule": LifecycleStatus.SCHEDULED,
        "upstream_failed": LifecycleStatus.ERROR,
        "skipped": LifecycleStatus.CANCELED,
        "removed": LifecycleStatus.CANCELED,
    }

    workflow_engine = "kaapana-plugin"

    def __init__(self, extra_headers: Optional[Dict[str, str]] = None):
        """
        Initializes the AirflowAdapter.

        Args:
            airflow_base_url (str): The base URL for the Airflow API.
            extra_headers (Optional[Dict[str, str]]): Additional headers to include in requests.
        """
        self.base_url = (
            "http://airflow-webserver-service.services.svc:8080/flow/kaapana/api"
        )
        self.extra_headers = {}
        super().__init__()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
        json: Dict[str, Any] = None,
    ) -> Any:
        """
        Makes a synchronous HTTP request to the workflow engine API.
        Args:
            method (str): The HTTP method (e.g., "GET", "POST", "PATCH").
            endpoint (str): The API endpoint (e.g., "/dags/{dag_id}/dagRuns").
            params (Optional[Dict[str, Any]]): Query parameters for the request.
            json (Optional[Dict[str, Any]]): JSON payload for the request body.
        Returns:
            Any: The JSON response from the API, or text if content type is not JSON.
        Raises:
            RuntimeError: If the request fails or the response is not JSON.
        """
        url = f"{self.base_url}{endpoint}"
        self.logger.info(f"Making request to: {url} with headers: {self.extra_headers}")
        headers = {
            "Content-Type": "application/json",
            **self.extra_headers,
        }

        try:
            resp = requests.request(
                method, url, headers=headers, params=params, json=json
            )
            resp.raise_for_status()
            if "application/json" in resp.headers.get("Content-Type", ""):
                return resp.json()
            return resp.text
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error [{method} {url}]: {e}")
            raise RuntimeError(f"API request error: {e}")

    def post_workflow(self):
        pass

    def submit_workflow_run(
        self,
        workflow: schemas.Workflow,
        workflow_run: schemas.WorkflowRun,
    ) -> schemas.WorkflowRun:
        """ """

        dag_id = workflow.identifier
        config = workflow_run.config

        dag_run_id = (
            "undefiened"  # Placeholder, should be replaced with actual run ID logic
        )
        endpoint = (
            f"/trigger/{dag_id}"  # Reverted to the previous endpoint as requested
        )
        payload = {"dag_run_id": dag_run_id, "conf": config}

        response = self._request("POST", endpoint, json=payload)
        self.logger.info(f"Submitted workflow run to Airflow with DAG ID {dag_id}")
        # {'message': ['delete-series created!', {'dag_id': 'delete-series', 'run_id': 'delete-series-250723104127048483'}]}})

        # kaapana response: {'message': ['delete-series created!', {'dag_id': '<dag-id>', 'run_id': '<dag-id>-250723104127048483'}]}
        # dag_run_id = response['message'][1]['run_id']  # Use the ID from the response or fallback to dag_id
        dag_run_id = response.get("message", [{}])[1].get("run_id", dag_run_id)
        # Airflow's API typically returns the DAG run details upon successful submission
        # We'll use the status from the response or default to SCHEDULED
        airflow_status = response.get("state", "queued")
        lifecycle_status = KaapanaPluginAdapter.AIRFLOW_STATUS_MAPPER.get(
            airflow_status, LifecycleStatus.SCHEDULED
        )

        return crud.update_workflow_run(
            run_id=workflow_run.id,
            workflow_run_update=schemas.WorkflowRunUpdate(
                external_id=dag_run_id, lifecycle_status=lifecycle_status
            ),
        )

    def get_workflow_run(
        self, workflow_run: schemas.WorkflowRun
    ) -> schemas.WorkflowRun:
        """
        Gets the current status of a workflow run from Airflow.

        Args:
            dag_id (str): The ID of the DAG.
            dag_run_id (str): The ID of the DAG run.

        Returns:
            LifecycleStatus: The mapped lifecycle status of the workflow run.
        """
        dag_id = workflow_run.workflow_id
        dag_run_id = workflow_run.external_id

        endpoint = f"/dagdetails/{dag_id}/{dag_run_id}"  # Adjusted endpoint to match Airflow's API
        # endpoint = f"/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"
        response = self._request("GET", endpoint)
        self.logger.info(
            f"Retrieved status for DAG run {dag_run_id} (DAG: {dag_id}) - Response: {response}"
        )
        airflow_status = response.get(
            "state", "failed"
        )  # Default to failed if state is missing
        workflow_run.lifecycle_status = self.AIRFLOW_STATUS_MAPPER.get(
            airflow_status, LifecycleStatus.ERROR
        )
        return workflow_run

    def get_workflow_run_tasks(
        self, dag_id: str, dag_run_id: str
    ) -> List[Dict[str, Any]]:
        """
        Gets the tasks for a specific DAG run from Airflow.

        Args:
            dag_id (str): The ID of the DAG.
            dag_run_id (str): The ID of the DAG run.

        Returns:
            Dict[str, Any]: A dictionary containing task information.
        """
        # endpoint = f"/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances"
        # return self._request("GET", endpoint)
        endpoint = f"/get_dagrun_tasks/{dag_id}/{dag_run_id}"  # Adjusted endpoint to match Airflow's API
        response = self._request("POST", endpoint)
        if isinstance(response, dict):
            data = response
        elif hasattr(response, "json") and callable(response.json):
            data = response.json()
        else:
            raise TypeError(f"Unsupported response type: {type(response)}")

        tasks = list()
        for task_id, details in data.items():
            # Map Airflow's task states to our LifecycleStatus
            airflow_status = details.get("state", "unknown")
            status = self.AIRFLOW_STATUS_MAPPER.get(
                airflow_status, LifecycleStatus.PENDING
            )
            tasks.append(
                {
                    "task_id": task_id,
                    "status": status,
                    "execution_date": details.get("execution_date"),
                    "duration": details.get("duration"),
                    # "try_number": details.get("try_number", 1)
                }
            )
        return tasks

    def cancel_workflow_run(self, dag_id: str, dag_run_id: str) -> bool:
        """
        Attempts to cancel a workflow run in Airflow.
        Note: Airflow's REST API doesn't have a direct "cancel" endpoint for DAG runs.
        A common approach is to set its state to "failed" or "marked_for_reschedule"
        or clear tasks. For true cancellation, manual intervention or a custom Airflow
        operator might be needed. This implementation marks it as failed.

        Args:
            dag_id (str): The ID of the DAG.
            dag_run_id (str): The ID of the DAG run.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        # endpoint = f"/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"
        # payload = {"state": "failed"} # Mark as failed to stop execution
        # try:
        #     self._request("PATCH", endpoint, json=payload)
        endpoint = (
            f"/abort/{dag_id}/{dag_run_id}"  # Adjusted endpoint to match Airflow's API
        )
        try:
            self._request("POST", endpoint)
            self.logger.info(
                f"Attempted to mark DAG run {dag_run_id} (DAG: {dag_id}) as 'failed'."
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to mark DAG run {dag_run_id} as 'failed': {e}")
            return False

    def get_tasks(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        """
        Gets the tasks for a specific DAG run from Airflow.

        Args:
            dag_id (str): The ID of the DAG.
            dag_run_id (str): The ID of the DAG run.

        Returns:
            Dict[str, Any]: A dictionary containing task information.
        """
        endpoint = f"/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances"
        return self._request("GET", endpoint)

    def get_logs(
        self, dag_id: str, dag_run_id: str, task_id: str, try_number: int = 1
    ) -> str:
        """
        Gets the logs for a specific task instance from Airflow.

        Args:
            dag_id (str): The ID of the DAG.
            dag_run_id (str): The ID of the DAG run.
            task_id (str): The ID of the task instance.
            try_number (int): The attempt number of the task instance.

        Returns:
            str: The logs as a string.
        """
        endpoint = f"/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/{try_number}"
        return self._request("GET", endpoint)
