from typing import List, Dict, Any, Optional

from app.adapters.base import WorkflowEngineAdapter
from app import schemas, crud
from app.schemas import LifecycleStatus


class DummyAdapter(WorkflowEngineAdapter):
    """
    Airflow-specific adapter implementation for synchronous communication.
    This adapter handles submitting, monitoring, and canceling workflows
    via the Airflow API.
    """

    workflow_engine = "dummy"

    def __init__(self):
        super().__init__()

    def post_workflow(self):
        pass

    def submit_workflow_run(
        self,
        workflow: schemas.Workflow,
        workflow_run: schemas.WorkflowRun,
    ) -> schemas.WorkflowRun:
        """ """

        return crud.update_workflow_run(
            run_id=workflow_run.id,
            workflow_run_update=schemas.WorkflowRunUpdate(LifecycleStatus.COMPLETED),
        )

    def get_workflow_run(self, workflow_run: schemas.WorkflowRun) -> LifecycleStatus:
        """
        Gets the current status of a workflow run from Airflow.

        Args:
            dag_id (str): The ID of the DAG.
            dag_run_id (str): The ID of the DAG run.

        Returns:
            LifecycleStatus: The mapped lifecycle status of the workflow run.
        """
        return workflow_run

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
