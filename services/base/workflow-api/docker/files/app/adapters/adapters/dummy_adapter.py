import random
from typing import List

from app import schemas
from app.adapters.base import WorkflowEngineAdapter

from datetime import datetime, timezone

# module-level store for mocked statuses
_MOCKED_RUN_STATUSES: dict[str, schemas.WorkflowRunStatus] = {}
# module-level stores for mocked cleanup state — tests can force a run's
# cleanup to raise, and inspect which runs were cleaned.
_MOCKED_CLEAN_RAISES: set[str] = set()
_CLEANED_RUNS: set[str] = set()


class DummyAdapter(WorkflowEngineAdapter):
    """
    Dummy adapter for testing purposes
    """

    workflow_engine = "dummy"

    def __init__(self):
        super().__init__()

    async def get_workflow_tasks(
        self,
        revision: schemas.WorkflowRevision | schemas.WorkflowRef,
    ) -> List[schemas.TaskCreate]:
        self.logger.info(f"Fetching dummy tasks for revision ref: {revision}")
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

    async def submit_workflow_revision(
        self, revision: schemas.WorkflowRevision
    ) -> schemas.WorkflowRevision:
        return revision

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

    async def get_task_run_logs(
        self, task_run_external_id: str
    ) -> list[schemas.LogLine]:
        raw_log = await self.get_task_run_raw_logs(task_run_external_id)
        return self._parse_task_run_logs(raw_log)

    async def get_task_run_raw_logs(self, task_run_external_id: str) -> str:
        """
        Gets the raw logs of a task run from the engine.

        Args:
            task_run_external_id (str): The ID of the task run in the engine.
        Returns:
            str: The raw logs of the task run.
        """

        return f"Dummy logs for TaskRun {task_run_external_id}"

    def _parse_task_run_logs(self, raw_log: str) -> list[schemas.LogLine]:
        return [
            schemas.LogLine(
                time=datetime.now(tz=timezone.utc),
                severity="INFO",
                message=line,
            )
            for line in raw_log.splitlines()
            if line.strip()
        ]

    @staticmethod
    def make_cleanup_raise(external_id: str) -> None:
        """Tests force the next cleanup call for this run to raise."""
        _MOCKED_CLEAN_RAISES.add(external_id)

    @staticmethod
    def reset_cleanup_state() -> None:
        _MOCKED_CLEAN_RAISES.clear()
        _CLEANED_RUNS.clear()

    @staticmethod
    def was_cleaned(external_id: str) -> bool:
        return external_id in _CLEANED_RUNS

    async def clean_workflow_run_data(
        self, workflow_run_external_id: str, project_id: str
    ) -> None:
        if workflow_run_external_id in _MOCKED_CLEAN_RAISES:
            _MOCKED_CLEAN_RAISES.discard(workflow_run_external_id)
            raise RuntimeError(
                f"Simulated cleanup failure for {workflow_run_external_id}"
            )
        _CLEANED_RUNS.add(workflow_run_external_id)

    async def is_workflow_run_data_clean(
        self, workflow_run_external_id: str, project_id: str
    ) -> bool:
        return workflow_run_external_id in _CLEANED_RUNS
