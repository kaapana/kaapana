import time
from typing import List

from app.adapters.base import WorkflowEngineAdapter
from app import schemas


class DummyAdapter(WorkflowEngineAdapter):
    """
    Dummy adapter for testing purposes
    """

    workflow_engine = "dummy"

    def __init__(self):
        super().__init__()

    async def get_workflow_tasks(
        self, workflow: schemas.Workflow
    ) -> List[schemas.TaskCreate]:
        self.logger.info(f"Posting workflow to DummyAdapter: {workflow.title}")
        time.sleep(2)
        task1 = schemas.TaskCreate(
            title="dummy-task-1",
            display_name="Dummy Task 1",
            type="test",
            downstream_task_titles=["dummy-task-2"],
        )
        task2 = schemas.TaskCreate(
            title="dummy-task-2",
            display_name="Dummy Task 2",
            type="test",
            downstream_task_titles=[],
        )
        return [task1, task2]

    async def submit_workflow(self, workflow: schemas.Workflow) -> schemas.Workflow:
        return workflow

    async def submit_workflow_run(
        self,
        workflow_run: schemas.WorkflowRun,
    ) -> schemas.WorkflowRunUpdate:
        """ """
        time.sleep(1)
        # simulate sending run to the engine, getting it back and updating external_id and status=PENDING
        return schemas.WorkflowRunUpdate(
            external_id="dummy-workflow-run-external-id",
            lifecycle_status=schemas.WorkflowRunStatus.PENDING,
        )

    async def get_workflow_run_status(
        self, workflow_run_external_id: str
    ) -> schemas.WorkflowRunStatus:
        """
        Gets the current status of a workflow run from engine.

        Args:
            workflow_run_external_id (str): The ID of the workflow run in the engine.

        Returns:
            WorkflowRunStatus: The WorkflowRun object with updated status.
        """
        time.sleep(1)
        # simulate getting info from the workflow engine and updating status to COMPLETED
        return schemas.WorkflowRunStatus.RUNNING

    async def get_workflow_run_task_runs(
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
                lifecycle_status=schemas.TaskRunStatus.RUNNING,
            ),
            schemas.TaskRunUpdate(
                external_id="dummy-task-run-2-external-id",
                task_title="dummy-task-2",
                lifecycle_status=schemas.TaskRunStatus.RUNNING,
            ),
        ]

    async def cancel_workflow_run(
        self, workflow_run_external_id: str
    ) -> schemas.WorkflowRunStatus:
        """
        Cancels a running workflow run in the engine.

        Args:
            workflow_run_external_id (str): The ID of the workflow run in the engine.

        Returns:
            WorkflowRunStatus: The updated status of the workflow run as canceled.
        """
        return schemas.WorkflowRunStatus.CANCELED

    async def retry_workflow_run(
        self, workflow_run_external_id: str
    ) -> schemas.WorkflowRunStatus:
        """
        Retries a workflow run in the engine.

        Args:
            workflow_run_external_id (str): The ID of the workflow run in the engine.

        Returns:
            WorkflowRunStatus: The updated status of the workflow run.
        """
        return schemas.WorkflowRunStatus.PENDING

    async def get_task_run_logs(self, task_run_external_id: str) -> str:
        """
        Gets the logs of a task run from the engine.

        Args:
            task_run_external_id (str): The ID of the task run in the engine.
        Returns:
            str: The logs of the task run.
        """

        time.sleep(1)
        return f"Dummy logs for TaskRun {task_run_external_id}"
