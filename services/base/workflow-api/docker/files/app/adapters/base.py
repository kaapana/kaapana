import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from app import schemas


class WorkflowEngineAdapter(ABC):
    """Abstract base class for workflow engine adapters"""

    workflow_engine = "base"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def generate_run_id(self, dag_id: str) -> str:
        run_id = datetime.now().strftime("%y%m%d%H%M%S%f")
        return f"{dag_id}-{run_id}"

    @abstractmethod
    async def submit_workflow_revision(
        self, revision: schemas.WorkflowRevision
    ) -> schemas.WorkflowRevision:
        """
        Create a workflow revision in the engine
        """
        pass

    @abstractmethod
    async def get_workflow_tasks(
        self,
        revision: "schemas.WorkflowRevision | schemas.WorkflowRef",
    ) -> List[schemas.TaskCreate]:
        """
        Get tasks with task-to-downstream mappings by task titles
        """
        pass

    @abstractmethod
    async def submit_workflow_run(
        self,
        workflow_run: schemas.WorkflowRun,
        project_id: str,
    ) -> schemas.WorkflowRunUpdate:
        """
        Submit a workflow to the external engine

        Args:
            workflow_run (schemas.WorkflowRun): The workflow run to submit
            project_id (str): project_id extracted from the cookies

        Returns:
            schemas.WorkflowRunUpdate: externa_id and lifecycle_status of the submitted workflow run
        """
        pass

    @abstractmethod
    async def get_workflow_run_task_runs(
        self, workflow_run_external_id: str
    ) -> List[schemas.TaskRunUpdate]:
        """
        Get tasks for a workflow run from the external engine.

        Args:
            workflow_run_external_id (id): The id of the workflow run.

        Returns:
            List[schemas.TaskRunUpdate]: A list of TaskRunUpdate objects.
        """
        pass

    @abstractmethod
    async def get_workflow_run_status(
        self, workflow_run_external_id: str
    ) -> schemas.WorkflowRunStatus:
        """
        Get the current status of a workflow from the external engine

        Args:
            workflow_run_external_id (str): The external ID of the workflow run in the engine.

        Returns:
            schemas.WorkflowRun: The WorkflowRun object with updated status.
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_task_run_logs(self, task_run_external_id: str) -> str:
        """
        Gets the logs of a task run from the engine.

        Args:
            task_run_external_id (str): The ID of the task run in the engine.
        Returns:
            str: The logs of the task run.
        """
        pass

    @abstractmethod
    def parse_task_run_logs(self, raw_log: str) -> list[schemas.LogLine]:
        """
        Parses the raw log string from the engine into structured LogLine objects.

        Args:
            raw_log (str): Raw log text as returned by get_task_run_logs().
        Returns:
            list[LogLine]: Parsed and normalized log lines.
        """
        pass

    @abstractmethod
    async def clean_workflow_run_data(self, workflow_run_external_id: str) -> None:
        """
        Delete all on-disk data associated with a workflow run.

        Must be idempotent: a no-op if the data has already been removed.
        Raises on any other failure.

        Args:
            workflow_run_external_id (str): The external ID of the workflow run.
        """
        pass

    @abstractmethod
    async def get_workflow_run_data_size(self, workflow_run_external_id: str) -> int:
        """
        Return the total on-disk size (bytes) of the workflow run's data.

        Args:
            workflow_run_external_id (str): The external ID of the workflow run.

        Returns:
            int: Total bytes; 0 if the data directory is missing.
        """
        pass

    @abstractmethod
    async def is_workflow_run_data_clean(self, workflow_run_external_id: str) -> bool:
        """
        Verify that the workflow run's data directory has been removed
        (or is empty).

        Args:
            workflow_run_external_id (str): The external ID of the workflow run.

        Returns:
            bool: True if no data remains, False otherwise.
        """
        pass
