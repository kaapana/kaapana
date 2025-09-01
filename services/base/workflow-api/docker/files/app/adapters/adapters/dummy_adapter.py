import logging
import time
from typing import List, Dict, Any

from app.adapters.base import WorkflowEngineAdapter
from app import schemas, crud
from app.schemas import LifecycleStatus
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


class DummyAdapter(WorkflowEngineAdapter):
    """
    Dummy adapter for testing purposes
    """

    workflow_engine = "dummy"

    def __init__(self):
        super().__init__()

    async def submit_workflow(
        self, db: AsyncSession, workflow: schemas.Workflow
    ) -> bool:
        logger.info(f"Posting workflow to DummyAdapter: {workflow.title}")
        time.sleep(2)
        # TODO: add task2 should be a downstream task of task1, but since task1 comes first, adding task2 as downstream does not work
        # TODO: might need a `crud.add_downstream_task` method
        task1 = await crud.create_task(
            db=db,
            task=schemas.TaskCreate(
                title="dummy-task-1", display_name="Dummy Task 1", type="test"
            ),
            workflow_id=workflow.id,
        )
        task2 = await crud.create_task(
            db=db,
            task=schemas.TaskCreate(
                title="dummy-task-2",
                display_name="Dummy Task 2",
                type="test",
            ),
            workflow_id=workflow.id,
        )
        logger.info(
            f"Dummy adapter successfully added tasks: {task1.title}, {task2.title}"
        )
        return True

    def submit_workflow_run(
        self,
        workflow: schemas.Workflow,
        workflow_run: schemas.WorkflowRun,
    ) -> schemas.WorkflowRun:
        """ """
        time.sleep(5)
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
