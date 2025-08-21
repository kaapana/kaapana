from typing import List, Dict, Any, Optional

from app.adapters.base import WorkflowEngineAdapter
from app import schemas
from app.models import LifecycleStatus


class DummyAdapter(WorkflowEngineAdapter):
    """
    Airflow-specific adapter implementation for synchronous communication.
    This adapter handles submitting, monitoring, and canceling workflows
    via the Airflow API.
    """

    workflow_engine = "dummy"

    def __init__(self, extra_headers: Optional[Dict[str, str]] = None):
        super().__init__()

    def post_workflow(self):
        pass

    def submit_workflow_run(
        self,
        workflow: schemas.Workflow,
        workflow_run: schemas.WorkflowRun,
    ) -> schemas.WorkflowRunResult:
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
        return schemas.WorkflowRunResult(
            external_id="",
            status=LifecycleStatus.COMPLETED,
        )

    def get_workflow_run_status(
        self, workflow_run: schemas.WorkflowRun
    ) -> LifecycleStatus:
        """
        Gets the current status of a workflow run from Airflow.

        Args:
            dag_id (str): The ID of the DAG.
            dag_run_id (str): The ID of the DAG run.

        Returns:
            LifecycleStatus: The mapped lifecycle status of the workflow run.
        """
        return workflow_run.lifecycle_status

    def get_workflow_run_tasks(
        self, dag_id: str, dag_run_id: str
    ) -> List[Dict[str, Any]]:
        """
        Gets the tasks for a specific DAG run from Airflow.

        Returns:
            Dict[str, Any]: A dictionary containing task information.
        """
        return {}

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
        return True
