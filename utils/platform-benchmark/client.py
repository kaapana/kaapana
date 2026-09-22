"""Kaapana client: Keycloak form login (oauth2-proxy cookies) + Airflow REST API."""

from __future__ import annotations

import re

import requests
import urllib3


class KaapanaClient:
    def __init__(self, host: str, username: str, password: str, timeout: int = 30):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = False
        self._login(username, password)

    def _login(self, username: str, password: str) -> None:
        # /flow/home establishes the Airflow flask session its API auth needs.
        r = self.session.get(f"{self.host}/", timeout=self.timeout)
        m = re.search(r'action="([^"]+)"', r.text)
        if not m:
            raise RuntimeError("Keycloak login form not found on landing page")
        action = m.group(1).replace("&amp;", "&")
        r = self.session.post(action, data={"username": username, "password": password}, timeout=self.timeout)
        if "login-actions" in r.url:
            raise RuntimeError("Login failed — check username/password")
        self.session.get(f"{self.host}/flow/home", timeout=self.timeout)

    def _get(self, path: str, **params):
        r = self.session.get(f"{self.host}/flow/api/v1{path}", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_dag_runs(self, dag_id: str, since: str | None, limit: int) -> list[dict]:
        params = {"limit": min(limit, 100), "order_by": "-start_date"}
        if since:
            # Airflow requires an explicit offset; the slice skips the date's dashes
            has_offset = "+" in since or since.endswith("Z") or "-" in since[11:]
            params["start_date_gte"] = since if has_offset else since + "+00:00"
        return self._get(f"/dags/{dag_id}/dagRuns", **params)["dag_runs"][:limit]

    def get_task_instances(self, dag_id: str, dag_run_id: str) -> list[dict]:
        return self._get(f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances", limit=250)["task_instances"]

    def get_dag_tasks(self, dag_id: str) -> list[dict]:
        return self._get(f"/dags/{dag_id}/tasks")["tasks"]

    def trigger_workflow(self, dag_id: str, identifiers: list[str], workflow_form: dict | None = None) -> None:
        if not getattr(self, "_project", None):
            self._project = next(
                p
                for p in self.session.get(f"{self.host}/aii/projects", timeout=self.timeout).json()
                if p["name"] == "admin"
            )
            self._project_prefix = f"/project/{self._project['id']}"
            self._instance = self.session.get(
                f"{self.host}/kaapana-backend/client/kaapana-instance", timeout=self.timeout
            ).json()["instance_name"]
        payload = {
            "dag_id": dag_id,
            "workflow_name": f"bench-{dag_id}",
            "conf_data": {"data_form": {"identifiers": identifiers}, "workflow_form": workflow_form or {}},
            "instance_names": [self._instance],
            "username": "kaapana",
        }
        r = self.session.post(
            f"{self.host}{self._project_prefix}/kaapana-backend/client/workflow", json=payload, timeout=60
        )
        if not r.ok:
            raise RuntimeError(f"{r.status_code} {r.reason} for {r.url}: {r.text[:500]}")

    def query_range(self, promql: str, minutes: int, step: int = 15) -> list[dict]:
        r = self.session.get(
            f"{self.host}{self._project_prefix}/kaapana-backend/monitoring/query-range/benchmark",
            params={"q": promql, "minutes": minutes, "step": step},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def get_task_log(self, dag_id: str, dag_run_id: str, task_id: str, try_number: int) -> str:
        r = self.session.get(
            f"{self.host}/flow/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/{try_number}",
            params={"full_content": "true"},
            headers={"Accept": "text/plain"},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.text
