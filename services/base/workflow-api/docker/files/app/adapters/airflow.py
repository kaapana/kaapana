import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.adapters.base import WorkflowEngineBase
from app.schemas import WorkflowRunResult
from app.models import LifecycleStatus


class AirflowAdapter(WorkflowEngineBase):
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

    def __init__(
        self, airflow_base_url: str, extra_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initializes the AirflowAdapter.

        Args:
            airflow_base_url (str): The base URL for the Airflow API.
            extra_headers (Optional[Dict[str, str]]): Additional headers to include in requests.
        """
        self.base_url = airflow_base_url
        self.extra_headers = extra_headers
        # TODO change to airflow API endpoint, the auth has to be adapted
        super().__init__()

    def trigger_workflow_run(
        self,
        workflow_run_id: int,
        workflow_identifier: str,
        config: Dict[str, Any],
        labels: Dict[str, str] = None,
    ) -> WorkflowRunResult:
        """
        Submits a new workflow run to Airflow.

        Args:
            workflow_run_id (int): The internal ID of the workflow run.
            workflow_identifier (str): The identifier of the workflow (e.g., DAG ID).
            config (Dict[str, Any]): Configuration for the workflow run.
            labels (Optional[Dict[str, str]]): Labels for the workflow run (not directly used by Airflow).

        Returns:
            WorkflowRunResult: The result of the submission, including external ID and status.
        """

        dag_id = workflow_identifier

        # TODO change to airflow API endpoint
        # endpoint = f"/dags/{dag_id}/dagRuns"
        # dag_run_id = self.generate_run_id(workflow_identifier)
        # dag_run_id is generated in kaapana endpoint
        dag_run_id = (
            "undefiened"  # Placeholder, should be replaced with actual run ID logic
        )
        endpoint = (
            f"/trigger/{dag_id}"  # Reverted to the previous endpoint as requested
        )
        payload = {"dag_run_id": dag_run_id, "conf": config}

        response = self._request("POST", endpoint, json=payload)
        self.logger.info(
            f"Submitted workflow run {workflow_run_id} to Airflow with DAG ID {dag_id}"
        )
        # {'message': ['delete-series created!', {'dag_id': 'delete-series', 'run_id': 'delete-series-250723104127048483'}]}})

        # kaapana response: {'message': ['delete-series created!', {'dag_id': '<dag-id>', 'run_id': '<dag-id>-250723104127048483'}]}
        # dag_run_id = response['message'][1]['run_id']  # Use the ID from the response or fallback to dag_id
        dag_run_id = response.get("message", [{}])[1].get("run_id", dag_run_id)
        # Airflow's API typically returns the DAG run details upon successful submission
        # We'll use the status from the response or default to SCHEDULED
        airflow_status = response.get("state", "queued")
        lifecycle_status = self.AIRFLOW_STATUS_MAPPER.get(
            airflow_status, LifecycleStatus.SCHEDULED
        )

        return WorkflowRunResult(
            workflow_run_id=workflow_run_id,
            external_id=dag_run_id,
            status=lifecycle_status,
            metadata={
                "dag_id": dag_id,
                "submitted_at": datetime.utcnow().isoformat(),
                "airflow_response": response,  # Store the full Airflow response for debugging
            },
        )

    def get_workflow_run_status(self, dag_id: str, dag_run_id: str) -> LifecycleStatus:
        """
        Gets the current status of a workflow run from Airflow.

        Args:
            dag_id (str): The ID of the DAG.
            dag_run_id (str): The ID of the DAG run.

        Returns:
            LifecycleStatus: The mapped lifecycle status of the workflow run.
        """
        endpoint = f"/dagdetails/{dag_id}/{dag_run_id}"  # Adjusted endpoint to match Airflow's API
        # endpoint = f"/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"
        response = self._request("GET", endpoint)
        self.logger.info(
            f"Retrieved status for DAG run {dag_run_id} (DAG: {dag_id}) - Response: {response}"
        )
        airflow_status = response.get(
            "state", "failed"
        )  # Default to failed if state is missing
        return self.AIRFLOW_STATUS_MAPPER.get(airflow_status, LifecycleStatus.ERROR)

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
