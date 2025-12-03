import asyncio
import shutil
from pathlib import Path
import os
from typing import List, Tuple, Optional
import httpx
import base64

from app import schemas
from app.adapters.base import WorkflowEngineAdapter


class KaapanaPluginAdapter(WorkflowEngineAdapter):
    # TODO: change name to airflow
    workflow_engine = "kaapana-plugin"

    def __init__(self):
        super().__init__()
        # config
        self.base_url = os.getenv(
            "AIRFLOW_API_URL", "http://airflow-webserver-service:8080/flow/api/v1"
        )
        self.k8s_namespace = os.getenv("SERVICES_NAMESPACE", "services")
        self.airflow_dag_folder = Path(
            os.getenv("AIRFLOW_DAG_FOLDER", "/kaapana/mounted/workflows/dags")
        )
        self.api_username = os.getenv("AIRFLOW_API_USERNAME")
        self.api_password = os.getenv("AIRFLOW_API_PASSWORD")

        # check if volume is mounted (fail fast)
        if not self.airflow_dag_folder.exists():
            self.logger.error(
                f"Airflow DAG mount path '{self.airflow_dag_folder}' not found. Check deployment volumes."
            )

        # check if Airflow API credentials are set
        if not self.api_username or not self.api_password:
            self.logger.error(
                "AIRFLOW_API_USERNAME or AIRFLOW_API_PASSWORD environment variables are missing!"
            )

    def _get_composite_id(self, dag_id: str, run_id: str) -> str:
        return f"{dag_id}::{run_id}"

    def _parse_composite_id(self, external_id: str) -> Tuple[str, str]:
        if not external_id or "::" not in external_id:
            raise ValueError(f"Invalid external_id format: {external_id}")
        dag_id, run_id = external_id.split("::", 1)
        return dag_id, run_id

    async def _request(self, method: str, endpoint: str, json: dict = {}) -> dict:
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=10.0) as client:

            if not self.api_username or not self.api_password:
                raise ConnectionRefusedError("Airflow API credentials are not set.")

            auth_string = f"{self.api_username}:{self.api_password}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {encoded_auth}",
            }
            resp = await client.request(
                method,
                url,
                headers=headers,
                json=json,
            )
            if resp.status_code == 404:
                raise FileNotFoundError(f"Resource not found at {url}")
            resp.raise_for_status()
            return resp.json()

    async def submit_workflow(self, workflow: schemas.Workflow) -> schemas.Workflow:
        """
        Writes the DAG definition directly to the shared PVC.
        Atomic-like write pattern (write temp -> rename) ensures Airflow doesn't pick up partial files.
        """
        self.logger.info(f"Writing DAG {workflow.title} to {self.airflow_dag_folder}")

        target_path = self.airflow_dag_folder / f"{workflow.title}.py"
        temp_path = self.airflow_dag_folder / f"{workflow.title}.py.tmp"

        try:
            # write to a .tmp file first so Airflow doesn't parse half written files
            with open(temp_path, "w") as f:
                f.write(workflow.definition)

            # atomic move
            shutil.move(str(temp_path), str(target_path))

            # ensure group can read/write
            try:
                os.chmod(target_path, 0o664)
            except PermissionError:
                self.logger.warning("Could not chmod DAG file. Check PVC permissions.")

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            self.logger.error(f"Failed to write DAG file: {e}")
            raise RuntimeError(f"Failed to persist DAG: {e}")

        return workflow

    async def get_workflow_tasks(
        self, workflow: schemas.Workflow
    ) -> List[schemas.TaskCreate]:
        """
        Polls the Airflow API until the DAG is found or timeout is reached.
        Once found, retrieves the tasks of the DAG.
        Args:
            workflow: The workflow whose tasks to retrieve
        Raises:
            RuntimeError: If the DAG is not found within the timeout period
        """
        dag_id = workflow.title
        max_retries = 10
        delay = 5
        timeout = 120
        start_time = asyncio.get_event_loop().time()

        for i in range(max_retries):
            # check absolute timeout before retrying
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(
                    f"DAG {dag_id} was not found in Airflow within the {timeout}s timeout. Check scheduler logs for import errors."
                )

            try:
                data = await self._request("GET", f"/dags/{dag_id}/tasks")
                tasks_data = data.get("tasks", [])
                res = []
                for t in tasks_data:
                    res.append(
                        schemas.TaskCreate(
                            title=t["task_id"],
                            display_name=t.get("ui_color", t["task_id"]),
                            type=t.get("class_ref", {}).get("class_name", "Operator"),
                            downstream_task_titles=t.get("downstream_task_ids", []),
                        )
                    )
                return res
            except FileNotFoundError:
                self.logger.info(
                    f"DAG {dag_id} not yet parsed. Retrying {i+1}/{max_retries}..."
                )
                await asyncio.sleep(delay)
                delay *= 1.5

        raise RuntimeError(f"DAG {dag_id} was not found in Airflow.")

    async def submit_workflow_run(
        self, workflow_run: schemas.WorkflowRun
    ) -> schemas.WorkflowRunUpdate:
        dag_id = workflow_run.workflow.title
        # Logic to extract/format parameters would go here
        payload = {"conf": {}}

        resp = await self._request("POST", f"/dags/{dag_id}/dagRuns", json=payload)
        airflow_run_id = resp["dag_run_id"]
        composite_id = self._get_composite_id(dag_id, airflow_run_id)

        return schemas.WorkflowRunUpdate(
            external_id=composite_id, lifecycle_status=schemas.WorkflowRunStatus.PENDING
        )

    async def get_workflow_run_status(
        self, workflow_run_external_id: str
    ) -> schemas.WorkflowRunStatus:
        dag_id, run_id = self._parse_composite_id(workflow_run_external_id)
        try:
            resp = await self._request("GET", f"/dags/{dag_id}/dagRuns/{run_id}")
        except FileNotFoundError:
            return schemas.WorkflowRunStatus.ERROR

        return self._map_workflow_run_state(resp.get("state"))

    async def get_workflow_run_task_runs(
        self, workflow_run_external_id: str
    ) -> List[schemas.TaskRunUpdate]:
        dag_id, run_id = self._parse_composite_id(workflow_run_external_id)

        data = await self._request(
            "GET", f"/dags/{dag_id}/dagRuns/{run_id}/taskInstances"
        )
        tasks = []
        for ti in data.get("task_instances", []):
            task_id = ti["task_id"]
            ti_external_id = f"{dag_id}::{run_id}::{task_id}"

            tasks.append(
                schemas.TaskRunUpdate(
                    external_id=ti_external_id,
                    task_title=task_id,
                    lifecycle_status=self._map_task_run_state(ti.get("state")),
                )
            )
        return tasks

    async def cancel_workflow_run(
        self, workflow_run: schemas.WorkflowRun
    ) -> schemas.WorkflowRunStatus:
        dag_id, run_id = self._parse_composite_id(workflow_run.external_id)
        payload = {"state": "failed"}
        await self._request("PATCH", f"/dags/{dag_id}/dagRuns/{run_id}", json=payload)
        return schemas.WorkflowRunStatus.CANCELED

    async def retry_workflow_run(
        self, workflow_run_external_id: str
    ) -> schemas.WorkflowRunStatus:
        dag_id, run_id = self._parse_composite_id(workflow_run_external_id)
        try:
            await self._request(
                "POST",
                f"/dags/{dag_id}/dagRuns/{run_id}/clear",
                json={"dry_run": False},
            )
        except FileNotFoundError:
            raise RuntimeError("Could not retry workflow. Run not found.")
        return schemas.WorkflowRunStatus.PENDING

    async def get_task_run_logs(self, task_run_external_id: str) -> str:
        parts = task_run_external_id.split("::")
        if len(parts) != 3:
            return "Log unavailable: Invalid ID format"
        dag_id, run_id, task_id = parts
        try_number = 1
        try:
            resp = await self._request(
                "GET",
                f"/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}",
            )
            if isinstance(resp, dict) and "content" in resp:
                return resp["content"]
            return str(resp)
        except Exception as e:
            return f"Failed to fetch logs: {e}"

    def _map_workflow_run_state(
        self, state: Optional[str]
    ) -> schemas.WorkflowRunStatus:
        """
        Maps Airflow DAG Run states to Kaapana WorkflowRunStatus.
        NOTE: WorkflowRunStatus does NOT have SKIPPED.
        """
        if not state:
            return schemas.WorkflowRunStatus.PENDING

        mapper = {
            "success": schemas.WorkflowRunStatus.COMPLETED,
            "failed": schemas.WorkflowRunStatus.ERROR,
            "upstream_failed": schemas.WorkflowRunStatus.ERROR,
            "queued": schemas.WorkflowRunStatus.SCHEDULED,
            "running": schemas.WorkflowRunStatus.RUNNING,
            "restarting": schemas.WorkflowRunStatus.RUNNING,
            "up_for_retry": schemas.WorkflowRunStatus.RUNNING,
            "scheduled": schemas.WorkflowRunStatus.SCHEDULED,
            "deferred": schemas.WorkflowRunStatus.PENDING,
            # If a whole DAG run is skipped, it is treated as cancelled.
            "skipped": schemas.WorkflowRunStatus.CANCELED,
        }
        return mapper.get(state, schemas.WorkflowRunStatus.RUNNING)

    def _map_task_run_state(self, state: Optional[str]) -> schemas.TaskRunStatus:
        """
        Maps Airflow Task Instance states to Kaapana TaskRunStatus.
        NOTE: TaskRunStatus DOES have SKIPPED.
        """
        if not state:
            return schemas.TaskRunStatus.PENDING

        mapper = {
            "success": schemas.TaskRunStatus.COMPLETED,
            "failed": schemas.TaskRunStatus.ERROR,
            "upstream_failed": schemas.TaskRunStatus.ERROR,
            "queued": schemas.TaskRunStatus.SCHEDULED,
            "running": schemas.TaskRunStatus.RUNNING,
            "restarting": schemas.TaskRunStatus.RUNNING,
            "up_for_retry": schemas.TaskRunStatus.RUNNING,
            "scheduled": schemas.TaskRunStatus.SCHEDULED,
            "deferred": schemas.TaskRunStatus.PENDING,
            # TaskRunStatus has SKIPPED
            "skipped": schemas.TaskRunStatus.SKIPPED,
            "removed": schemas.TaskRunStatus.SKIPPED,
        }
        # Default fallback
        return mapper.get(state, schemas.TaskRunStatus.RUNNING)
