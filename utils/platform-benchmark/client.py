from __future__ import annotations

import requests
from kaapana_auth import KaapanaAuth


class KaapanaClient(KaapanaAuth):
    def __init__(self, host: str, username: str, password: str, client_secret: str | None = None, timeout: int = 30):
        super().__init__(host, client_secret, username=username, password=password)
        self.timeout = timeout
        self.airflow_login()
        self._instance = None

    def _get(self, path: str, **params):
        return self.request(f"flow/api/v1{path}", params=params, timeout=self.timeout).json()

    def get_dag_runs(self, dag_id: str, since: str | None, limit: int) -> list[dict]:
        params = {"limit": min(limit, 100), "order_by": "-start_date"}
        if since:
            has_offset = "+" in since or since.endswith("Z") or "-" in since[11:]
            params["start_date_gte"] = since if has_offset else since + "+00:00"
        return self._get(f"/dags/{dag_id}/dagRuns", **params)["dag_runs"][:limit]

    def get_task_instances(self, dag_id: str, dag_run_id: str) -> list[dict]:
        return self._get(f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances", limit=250)["task_instances"]

    def get_dag_tasks(self, dag_id: str) -> list[dict]:
        return self._get(f"/dags/{dag_id}/tasks")["tasks"]

    def trigger_workflow(self, dag_id: str, identifiers: list[str], workflow_form: dict | None = None) -> None:
        if not self._instance:
            self._instance = self.request("kaapana-backend/client/kaapana-instance", timeout=self.timeout).json()[
                "instance_name"
            ]
        payload = {
            "dag_id": dag_id,
            "workflow_name": f"bench-{dag_id}",
            "conf_data": {"data_form": {"identifiers": identifiers}, "workflow_form": workflow_form or {}},
            "instance_names": [self._instance],
            "username": self.username,
        }
        r = self.request(
            "kaapana-backend/client/workflow",
            request_type=requests.post,
            _json=payload,
            timeout=60,
            retries=1,
            raise_for_status=False,
        )
        if not r.ok:
            raise RuntimeError(f"{r.status_code} {r.reason} for {r.url}: {r.text[:500]}")

    def query_range(self, promql: str, minutes: int, step: int = 15) -> list[dict]:
        return self.request(
            "kaapana-backend/monitoring/query-range/benchmark",
            params={"q": promql, "minutes": minutes, "step": step},
            timeout=self.timeout,
        ).json()

    def get_task_log(self, dag_id: str, dag_run_id: str, task_id: str, try_number: int) -> str:
        return self.request(
            f"flow/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/{try_number}",
            params={"full_content": "true"},
            headers={"Accept": "text/plain"},
            timeout=self.timeout,
        ).text
