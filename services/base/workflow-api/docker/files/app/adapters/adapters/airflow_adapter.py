import asyncio
import base64
import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple, Any
import json as jsonlib

import httpx
from app import schemas
from app.adapters.base import WorkflowEngineAdapter
from jinja2 import Template

import re
from ast import literal_eval
from datetime import datetime, timezone


class AirflowPluginAdapter(WorkflowEngineAdapter):
    workflow_engine = "airflow"  # TODO: change it to Airflow v2 when we have a separate adapter for Airflow v3
    # Airflow log format: [2025-05-01T12:34:56.789+00:00] {file.py:42} INFO - message
    _LOG_LINE_RE = re.compile(
        r"^\[(?P<ts>[^\]]+)\]\s+\{(?P<loc>[^}]*)\}\s+(?P<level>[A-Z]+)\s+-\s*(?P<msg>.*)$"
    )
    _BARE_LEVEL_RE = re.compile(r"^(?P<level>[A-Z]+)\s+-\s*(?P<msg>.*)$")
    _TS_OFFSET_RE = re.compile(r"([+-]\d{2})(\d{2})$")
    _KNOWN_LEVELS = {"DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL"}

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

        # ensure KaapanaTaskOperator is present in DAGs directory for imports
        try:
            self._ensure_kaapana_task_operator()
        except Exception as e:
            self.logger.error(f"Failed to stage KaapanaTaskOperator.py: {e}")

    def _get_composite_id(self, dag_id: str, run_id: str) -> str:
        return f"{dag_id}::{run_id}"

    def _parse_composite_id(self, external_id: str) -> Tuple[str, str]:
        if not external_id or "::" not in external_id:
            raise ValueError(f"Invalid external_id format: {external_id}")
        dag_id, run_id = external_id.split("::", 1)
        return dag_id, run_id

    @staticmethod
    def _sanitize_for_dag_id(title: str) -> str:
        """
        Replace chars that are not accepted by Airflow `dag_id` with an underscore."""
        import re

        return re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("_")

    def _get_dag_id_from_workflow(self, title: str, increment: int) -> str:
        """Create a DAG ID from a workflow title and revision increment."""
        return f"{self._sanitize_for_dag_id(title)}_inc{increment}"

    def _map_workflow_run_state(
        self, state: Optional[str]
    ) -> schemas.WorkflowRunStatus:
        """
        Maps Airflow DAG Run states to Kaapana WorkflowRunStatus.
        """
        if not state:
            return schemas.WorkflowRunStatus.PENDING

        mapper = {
            "success": schemas.WorkflowRunStatus.COMPLETED,
            "failed": schemas.WorkflowRunStatus.ERROR,
            "queued": schemas.WorkflowRunStatus.SCHEDULED,
            "running": schemas.WorkflowRunStatus.RUNNING,
        }
        if state not in mapper:
            raise RuntimeError(f"Unknown workflow run state: {state}")
        return mapper[state]

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
            "upstream_failed": schemas.TaskRunStatus.UPSTREAM_FAILED,
            "queued": schemas.TaskRunStatus.SCHEDULED,
            "running": schemas.TaskRunStatus.RUNNING,
            "restarting": schemas.TaskRunStatus.RUNNING,
            "up_for_retry": schemas.TaskRunStatus.RUNNING,
            "up_for_reschedule": schemas.TaskRunStatus.RUNNING,
            "scheduled": schemas.TaskRunStatus.SCHEDULED,
            "deferred": schemas.TaskRunStatus.PENDING,
            "skipped": schemas.TaskRunStatus.SKIPPED,
            "removed": schemas.TaskRunStatus.SKIPPED,
        }
        if state not in mapper:
            raise RuntimeError(f"Unknown task run state: {state}")
        return mapper[state]

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: dict = {},
        accepted_content_types: tuple[str, ...] = ("application/json",),
    ) -> dict | Any:
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=10.0) as client:

            if not self.api_username or not self.api_password:
                raise ConnectionRefusedError("Airflow API credentials are not set.")

            auth_string = f"{self.api_username}:{self.api_password}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {encoded_auth}",
                "Accept": "application/json",
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

            content_type = resp.headers.get("content-type", "").split(";")[0].strip()

            if content_type not in accepted_content_types:
                raise RuntimeError(
                    f"Unexpected response content type from {method} {url}: "
                    f"{content_type or '<missing>'}"
                )

            if content_type == "application/json":
                return resp.json()

            if content_type == "text/plain":
                return resp.text

            raise RuntimeError(f"Unsupported response content type: {content_type}")

    async def submit_workflow_revision(
        self, revision: schemas.WorkflowRevision
    ) -> schemas.WorkflowRevision:
        """
        Writes a workflow revision's DAG definition directly to the shared PVC.
        Atomic-like write pattern (write temp -> rename) ensures Airflow doesn't pick up partial files.
        """
        dag_id = self._get_dag_id_from_workflow(revision.workflow_title, revision.increment)
        dag_filename = f"{dag_id}.py"
        temp_filename = f"{dag_id}.py.tmp"

        target_path = self.airflow_dag_folder / dag_filename
        temp_path = self.airflow_dag_folder / temp_filename

        self.logger.info(
            f"Rendering DAG template for workflow {revision.workflow_id} "
            f"inc{revision.increment} as {dag_filename}"
        )

        try:
            template = Template(revision.definition)
            rendered_definition = template.render(dag_id=dag_id)
        except Exception as e:
            self.logger.error(f"Failed to render DAG template: {e}")
            raise RuntimeError(f"Failed to render DAG template: {e}")

        self.logger.info(
            f"Writing rendered DAG {dag_filename} to {self.airflow_dag_folder}"
        )

        try:
            # write to a .tmp file first so Airflow doesn't parse half written files
            with open(temp_path, "w") as f:
                f.write(rendered_definition)

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

        return revision

    def _ensure_kaapana_task_operator(self) -> None:
        """Copy KaapanaTaskOperator.py into the Airflow DAGs folder if missing.
        This allows DAGs to import the operator without additional Python path tweaks.
        """
        self.logger.info(
            "Ensuring KaapanaTaskOperator.py is present in Airflow DAGs folder..."
        )
        src = (
            Path(__file__).resolve().parent.parent
            / "engine_utils"
            / "KaapanaTaskOperator.py"
        )
        dst = self.airflow_dag_folder / "task_api_operators" / "KaapanaTaskOperator.py"

        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)

        if not src.exists():
            raise FileNotFoundError(f"Source operator not found: {src}")

        try:
            # If destination missing or different size/mtime, copy
            if not dst.exists():
                shutil.copy2(src, dst)
                try:
                    os.chmod(dst, 0o664)
                except PermissionError:
                    self.logger.warning(
                        "Could not chmod operator file. Check PVC permissions."
                    )
                self.logger.info(f"Staged operator: {dst}")
        except Exception as e:
            raise RuntimeError(f"Failed to copy operator: {e}")

    async def get_workflow_tasks(
        self,
        revision: schemas.WorkflowRevision | schemas.WorkflowRef,
    ) -> List[schemas.TaskCreate]:
        """
        Polls the Airflow API until the DAG is found or timeout is reached.
        Once found, retrieves the tasks of the DAG.
        Args:
            revision: Anything that resolves to a DAG id (WorkflowRevision or WorkflowRef).
        Raises:
            RuntimeError: If the DAG is not found within the timeout period
        """
        title = (
            revision.workflow_title
            if isinstance(revision, schemas.WorkflowRevision)
            else revision.title
        )
        dag_id = self._get_dag_id_from_workflow(title, revision.increment)
        max_retries = 10
        delay = 5.0
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
                    f"DAG {dag_id} not yet parsed. Retrying {i + 1}/{max_retries}..."
                )
                await asyncio.sleep(delay)
                delay *= 1.5

        raise RuntimeError(f"DAG {dag_id} was not found in Airflow.")

    async def _fetch_project(self, project_id: str) -> dict:
        aii_url = os.getenv(
            "ACCESS_INFORMATION_INTERFACE_URL", "http://aii-service.services.svc:8080"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{aii_url}/projects/{project_id}", timeout=10)
            resp.raise_for_status()
            return resp.json()

    async def submit_workflow_run(
        self, workflow_run: schemas.WorkflowRun, project_id: str
    ) -> schemas.WorkflowRunUpdate:
        # workflow_run.workflow is a WorkflowRef(id, title, increment) — enough for dag_id
        ref = workflow_run.workflow
        dag_id = self._get_dag_id_from_workflow(ref.title, ref.increment)
        payload: dict = {"conf": {}}

        project = await self._fetch_project(project_id)
        payload["conf"]["project_form"] = project

        # Inject project_id into all task envs
        tasks = await self.get_workflow_tasks(workflow_run.workflow)  # type: ignore
        payload["conf"]["task_form"] = {
            t.title: {
                "env": [{"name": "KAAPANA_PROJECT_IDENTIFIER", "value": project_id}]
            }
            for t in tasks
        }

        task_form = payload["conf"]["task_form"]

        def _to_env_str(value) -> str:
            # Env vars must be strings (BaseEnv.value: str); bools lowercased, lists/dicts JSON-encoded.
            if isinstance(value, str):
                return value
            if isinstance(value, bool):
                return "true" if value else "false"
            if value is None:
                return ""
            if isinstance(value, (int, float)):
                return str(value)
            return jsonlib.dumps(value)

        def _extract_param(param: schemas.WorkflowParameter):
            task_title = param.task_title
            env_name = param.env_variable_name
            ui_form = param.ui_form
            value = _to_env_str(getattr(ui_form, "default", None))
            return task_title, env_name, value

        for param in workflow_run.workflow_parameters:
            task_title, env_name, value = _extract_param(param)
            task_form.setdefault(task_title, {"env": []})["env"].append(
                {"name": env_name, "value": value}
            )

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
        self, workflow_run_external_id: str
    ) -> schemas.WorkflowRunStatus:
        dag_id, run_id = self._parse_composite_id(workflow_run_external_id)
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

        try:
            task_instance: dict = await self._request(
                "GET",
                f"/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}",
            )
            if (
                isinstance(task_instance, dict)
                and "try_number" in task_instance
                and task_instance["try_number"] > 0
            ):
                try_number = int(task_instance["try_number"])
            else:
                return f"No logs available for task instance {task_run_external_id} because it has not run yet."
        except Exception as e:
            return f"Failed to fetch task instance for logs {e}"

        resp = None
        try:
            resp = await self._request(
                "GET",
                f"/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}",
                accepted_content_types=("application/json",),  # "text/plain"),
            )
            if isinstance(resp, dict) and "content" in resp:
                return resp["content"]
            return str(resp)
        except Exception as e:
            return f"Failed to fetch logs: {e}\nResponse: {resp}"

    def parse_task_run_logs(self, raw_log: str) -> list[schemas.LogLine]:
        entries: list[schemas.LogLine] = []
        last_ts = datetime.now(tz=timezone.utc)

        # Airflow wraps log content as a Python repr of [(host, log_text), ...].
        # literal_eval is the intended way to decode this format.
        try:
            log_tuples: list[tuple[str, str]] = literal_eval(raw_log)
        except (ValueError, SyntaxError):
            # Not a tuple-list repr (e.g. plain-text error message) -> treat as single entry
            log_tuples = [("unknown", raw_log)]
        except Exception as e:
            self.logger.warning(f"Unexpected error parsing log: {e}")
            log_tuples = [("unknown", raw_log)]

        for _host, log_text in log_tuples:
            for raw_line in log_text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue

                # Case 1: line is in the format as expected
                m = self._LOG_LINE_RE.match(line)
                if m and m.group("level") in self._KNOWN_LEVELS:
                    last_ts = self._parse_ts(m.group("ts"))
                    entries.append(
                        schemas.LogLine(
                            time=last_ts,
                            severity=m.group("level"),
                            message=m.group("msg"),
                            metadata=(
                                {"location": m.group("loc")} if m.group("loc") else {}
                            ),
                        )
                    )
                    continue

                # Case 2: bare "INFO - ..."
                bare = self._BARE_LEVEL_RE.match(line)
                if bare and bare.group("level") in self._KNOWN_LEVELS:
                    entries.append(
                        schemas.LogLine(
                            time=last_ts,
                            severity=bare.group("level"),
                            message=bare.group("msg"),
                        )
                    )
                    continue

                # Case 3: *** meta lines
                if line.startswith("***"):
                    entries.append(
                        schemas.LogLine(
                            time=last_ts,
                            severity="DEBUG",
                            message=line.lstrip("* ").strip(),
                        )
                    )
        return entries

    @classmethod
    def _parse_ts(cls, ts: str) -> datetime:
        # fromisoformat requires a colon in the UTC offset ("+00:00"), but Airflow
        # sometimes emits "+0000" without it — normalize before parsing.
        normalized = cls._TS_OFFSET_RE.sub(r"\1:\2", ts)
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return datetime.now(tz=timezone.utc)
