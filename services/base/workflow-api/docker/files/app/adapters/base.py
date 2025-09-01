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
    async def submit_workflow_run(
        self, workflow: schemas.Workflow, workflow_run: schemas.WorkflowRun
    ) -> schemas.WorkflowRun:
        """Submit a workflow to the external engine"""
        pass

    @abstractmethod
    async def get_workflow_run_tasks(
        self, workflow_run: schemas.WorkflowRun
    ) -> List[schemas.TaskRun]:
        """
        Get tasks for a workflow run from the external engine.

        Args:
            workflow_identifier (str): The workflow identifier.
            external_id (str): The external ID of the workflow run.


        Returns:
            Dict[str, Any]: A dictionary containing task information.
        """
        pass

    @abstractmethod
    async def get_workflow_run(
        self, workflow_run: schemas.WorkflowRun
    ) -> schemas.WorkflowRun:
        """Get the current status of a workflow from the external engine"""
        pass

    @abstractmethod
    async def cancel_workflow_run(self, workflow_run: schemas.WorkflowRun) -> bool:
        """Cancel a workflow in the external engine"""
        pass

    @abstractmethod
    async def submit_workflow(
        self, db: AsyncSession, workflow: schemas.Workflow
    ) -> bool:
        """
        1. Create the workflow based on the definition in the WorkflowEngine
        2. Get tasks from workflow engine
        3. Create tasks in database
        """
