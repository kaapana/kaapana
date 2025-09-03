import logging
import time
from typing import List, Dict, Any

from app.adapters.base import WorkflowEngineAdapter
from app import schemas
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
        self, workflow: schemas.Workflow
    ) -> List[schemas.TaskCreate]:
        logger.info(f"Posting workflow to DummyAdapter: {workflow.title}")
        time.sleep(2)
        task1 = schemas.TaskCreate(
            title="dummy-task-1", display_name="Dummy Task 1", type="test"
        )
        task2 = schemas.TaskCreate(
            title="dummy-task-2",
            display_name="Dummy Task 2",
            type="test",
        )
        return [task1, task2]

    async def submit_workflow_run(
        self,
        workflow_run: schemas.WorkflowRun,
    ) -> schemas.WorkflowRunUpdate:
        """ """
        time.sleep(1)
        # simulate sending run to the engine, getting it back and updating external_id and status=PENDING
        return schemas.WorkflowRunUpdate(
            external_id="dummy-workflow-run-external-id",
            lifecycle_status=schemas.LifecycleStatus.PENDING,
        )

    async def get_workflow_run(
        self, workflow_run_external_id: str
    ) -> schemas.LifecycleStatus:
        """
        Gets the current status of a workflow run from engine.

        Args:
            workflow_run_external_id (str): The ID of the workflow run in the engine.

        Returns:
            LifecycleStatus: The WorkflowRun object with updated status.
        """
        time.sleep(1)
        # simulate getting info from the workflow engine and updating status to COMPLETED
        return schemas.LifecycleStatus.COMPLETED

    def get_workflow_run_task_runs(
        self, workflow_run_external_id: str
    ) -> List[schemas.TaskRunUpdate]:
        """
        Gets the task runs of a workflow run from Airflow.
        Args:
            workflow_run_external_id (str): The ID of the workflow run in the engine.   

        Returns:
            List[TaskRunUpdate]: List of TaskRunUpdate objects with updated status.
        """
        time.sleep(1)
        return [
            schemas.TaskRunUpdate(
                external_id="dummy-task-run-1-external-id",
                task_title="dummy-task-1",
                lifecycle_status=schemas.LifecycleStatus.COMPLETED,
            ),
            schemas.TaskRunUpdate(
                external_id="dummy-task-run-2-external-id",
                task_title="dummy-task-2",
                lifecycle_status=schemas.LifecycleStatus.COMPLETED,
            ),
        ]

    def cancel_workflow_run(
        self, workflow_run_external_id: str
    ) -> schemas.LifecycleStatus:
        """
        Cancels a running workflow run in the engine.

        Args:
            workflow_run_external_id (str): The ID of the workflow run in the engine.

        Returns:
            LifecycleStatus: The updated status of the workflow run as canceled.
        """
        return schemas.LifecycleStatus.CANCELED
