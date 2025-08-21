from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime
import requests
import logging
from app import schemas


class WorkflowEngineAdapter(ABC):
    """Abstract base class for workflow engine adapters"""

    workflow_engine = "base"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_run_id(self, dag_id: str) -> str:
        run_id = datetime.now().strftime("%y%m%d%H%M%S%f")
        return f"{dag_id}-{run_id}"

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
        json: Dict[str, Any] = None,
    ) -> Any:
        """
        Makes a synchronous HTTP request to the workflow engine API.
        Args:
            method (str): The HTTP method (e.g., "GET", "POST", "PATCH").
            endpoint (str): The API endpoint (e.g., "/dags/{dag_id}/dagRuns").
            params (Optional[Dict[str, Any]]): Query parameters for the request.
            json (Optional[Dict[str, Any]]): JSON payload for the request body.
        Returns:
            Any: The JSON response from the API, or text if content type is not JSON.
        Raises:
            RuntimeError: If the request fails or the response is not JSON.
        """
        url = f"{self.base_url}{endpoint}"
        self.logger.info(f"Making request to: {url} with headers: {self.extra_headers}")
        headers = {
            "Content-Type": "application/json",
            **self.extra_headers,
        }

        try:
            resp = requests.request(
                method, url, headers=headers, params=params, json=json
            )
            resp.raise_for_status()
            if "application/json" in resp.headers.get("Content-Type", ""):
                return resp.json()
            return resp.text
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error [{method} {url}]: {e}")
            raise RuntimeError(f"API request error: {e}")

    @abstractmethod
    def submit_workflow_run(
        self, workflow: schemas.Workflow, workflow_run: schemas.WorkflowRun
    ) -> schemas.WorkflowRunResult:
        """Submit a workflow to the external engine"""
        pass

    @abstractmethod
    def get_workflow_run_tasks(
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
    def get_workflow_run_status(
        self, workflow_run: schemas.WorkflowRun
    ) -> schemas.LifecycleStatus:
        """Get the current status of a workflow from the external engine"""
        pass

    @abstractmethod
    def cancel_workflow_run(self, workflow_run: schemas.WorkflowRun) -> bool:
        """Cancel a workflow in the external engine"""
        pass

    @abstractmethod
    def post_workflow(workflow: schemas.Workflow):
        """
        Create the workflow based on the definition in the WorkflowEngine
        """

    def _get_workflows(self):
        """
        Get Workflows from the database that are associated with the specific WorkflowEngineAdapter
        """

    def _get_workflows_runs(
        self,
        state: schemas.LifecycleStatus,
    ) -> List[schemas.WorkflowRun]:
        """
        Get all Workflow Run objects with state as LifecycleStatus
        """

    def _update_workflow_run_(self, update: schemas.WorkflowRun) -> schemas.WorkflowRun:
        """ """
