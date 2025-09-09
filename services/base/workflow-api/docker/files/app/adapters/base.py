from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
import logging
from app import schemas
from sqlalchemy.ext.asyncio import AsyncSession


class WorkflowEngineAdapter(ABC):
    """Abstract base class for workflow engine adapters"""

    workflow_engine = "base"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def generate_run_id(self, dag_id: str) -> str:
        run_id = datetime.now().strftime("%y%m%d%H%M%S%f")
        return f"{dag_id}-{run_id}"

    @abstractmethod
    async def submit_workflow(self, workflow: schemas.Workflow) -> schemas.Workflow:
        """
        Create a workflow in the engine
        """
        pass

    @abstractmethod
    async def get_workflow_tasks(
        self, workflow: schemas.Workflow
    ) -> List[schemas.TaskCreate]:
        """
        Get tasks with task-to-downstream mappings
        """
        pass

    @abstractmethod
    async def submit_workflow_run(
        self,
        workflow_run: schemas.WorkflowRun,
    ) -> schemas.WorkflowRunUpdate:
        """
        Submit a workflow to the external engine

        Args:
            workflow_run (schemas.WorkflowRun): The workflow run to submit

        Returns:
            schemas.WorkflowRunUpdate: externa_id and lifecycle_status of the submitted workflow run
        """
        pass

    @abstractmethod
    async def get_workflow_run_task_runs(
        self, workflow_run_external_id: int
    ) -> List[schemas.TaskRun]:
        """
        Get tasks for a workflow run from the external engine.

        Args:
            workflow_run_external_id (id): The id of the workflow run.

        Returns:
            List[schemas.TaskRun]: A list of TaskRun objects.
        """
        pass

    @abstractmethod
    async def get_workflow_run(
        self, workflow_run_external_id: str
    ) -> schemas.LifecycleStatus:
        """
        Get the current status of a workflow from the external engine

        Args:
            workflow_run_external_id (str): The external ID of the workflow run in the engine.

        Returns:
            schemas.WorkflowRun: The WorkflowRun object with updated status.
        """
        pass

    @abstractmethod
    async def cancel_workflow_run(self, workflow_run: schemas.WorkflowRun) -> bool:
        """Cancel a workflow in the external engine"""
        pass
