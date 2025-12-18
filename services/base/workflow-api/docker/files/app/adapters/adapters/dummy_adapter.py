import random
from typing import List

from app import schemas
from app.adapters.base import WorkflowEngineAdapter

# module-level store for mocked statuses
_MOCKED_RUN_STATUSES: dict[str, schemas.WorkflowRunStatus] = {}


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
        self, workflow_run: schemas.WorkflowRun, project_id: str
    ) -> schemas.WorkflowRunUpdate:
        """ """
        # simulate sending run to the engine, getting it back and updating external_id and status=PENDING
        return schemas.WorkflowRunUpdate(
            external_id=f"dummy-workflow-run-extid-{workflow_run.id}-{random.randint(0, 1000)}",
            lifecycle_status=schemas.WorkflowRunStatus.PENDING,
        )

    @staticmethod
    def set_status(external_id: str, status: schemas.WorkflowRunStatus):
        """Allows test clients to control the status returned for a specific run."""
        _MOCKED_RUN_STATUSES[external_id] = status

    @staticmethod
    def reset_statuses():
        """Clears the status dictionary."""
        _MOCKED_RUN_STATUSES.clear()

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
        # simulate getting info from the workflow engine and updating status to COMPLETED

        # 1. check if the status has been manually set by a test (NO MOCKS)
        if workflow_run_external_id in _MOCKED_RUN_STATUSES:
            return _MOCKED_RUN_STATUSES[workflow_run_external_id]

        # 2. Fallback to default behavior for all other cases
        # (This is your original hardcoded logic)
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
        return [
            schemas.TaskRunUpdate(
                external_id=f"dummy-taskrun-1-extid-{workflow_run_external_id}-{random.randint(0, 1000)}",
                task_title="dummy-task-1",
                lifecycle_status=schemas.TaskRunStatus.RUNNING,
            ),
            schemas.TaskRunUpdate(
                external_id=f"dummy-taskrun-2-extid-{workflow_run_external_id}-{random.randint(0, 1000)}",
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

        return f"Dummy logs for TaskRun {task_run_external_id}"
