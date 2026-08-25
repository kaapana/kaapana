"""Client for a deployed Kaapana platform: Keycloak login, then the Airflow
REST API (proxied at /flow) and the kaapana-backend workflow API.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from datetime import datetime

import requests
import urllib3

AIRFLOW_API = "/flow/api/v1"
PAGE_SIZE = 100
TERMINAL_STATES = ("success", "failed")

# Matches Keycloak's credential form specifically; the page also carries a
# locale form.
LOGIN_FORM_ACTION = re.compile(r'action="([^"]*login-actions/authenticate[^"]*)"')


class KaapanaClient:
    def __init__(self, host: str, username: str, password: str, timeout: int = 30):
        # Platform certificates are self-signed in every test deployment.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.host = host.rstrip("/")
        self.username = username
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = False
        self._project: dict | None = None
        self._instance: str | None = None
        self._login(password)

    def _login(self, password: str) -> None:
        landing = self.session.get(f"{self.host}/", timeout=self.timeout)
        match = LOGIN_FORM_ACTION.search(landing.text)
        if not match:
            raise RuntimeError(f"no Keycloak login form at {self.host}")
        action = match.group(1).replace("&amp;", "&")
        response = self.session.post(
            action,
            data={"username": self.username, "password": password},
            timeout=self.timeout,
        )
        if "login-actions" in response.url:
            raise RuntimeError(f"login as {self.username!r} was rejected")
        # Airflow's session auth backend needs one authenticated page view
        # before the REST API accepts the cookie.
        self.session.get(f"{self.host}/flow/home", timeout=self.timeout)

    def _get(self, path: str, **params) -> dict:
        response = self.session.get(
            f"{self.host}{AIRFLOW_API}{path}", params=params, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def dag_runs(self, dag_id: str, since: datetime) -> list[dict]:
        """Every run of *dag_id* triggered at or after *since*, all pages.

        Filtered on execution_date: a queued run has no start_date yet, so
        start_date hides the runs that pile up at the max_active_runs cap.
        """
        runs: list[dict] = []
        while True:
            page = self._get(
                f"/dags/{dag_id}/dagRuns",
                execution_date_gte=since.isoformat(),
                order_by="execution_date",
                limit=PAGE_SIZE,
                offset=len(runs),
            )["dag_runs"]
            runs += page
            if len(page) < PAGE_SIZE:
                return runs

    def active_run_count(self, dag_id: str) -> int:
        return self._get(
            f"/dags/{dag_id}/dagRuns", state=["queued", "running"], limit=1
        )["total_entries"]

    def task_instances(self, dag_id: str, dag_run_id: str) -> list[dict]:
        instances: list[dict] = []
        while True:
            page = self._get(
                f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances",
                limit=PAGE_SIZE,
                offset=len(instances),
            )["task_instances"]
            instances += page
            if len(page) < PAGE_SIZE:
                return instances

    def _authorise_project(self) -> None:
        if self._project is None:
            projects = self.session.get(
                f"{self.host}/aii/projects", timeout=self.timeout
            ).json()
            self._project = next(p for p in projects if p["name"] == "admin")
            self._instance = self.session.get(
                f"{self.host}/kaapana-backend/client/kaapana-instance", timeout=self.timeout
            ).json()["instance_name"]
            # The auth backend re-reads this cookie to inject the Project header
            # the backend requires. The domain must carry no port.
            domain = urllib.parse.urlsplit(self.host).hostname
            self.session.cookies.set(
                "Project",
                urllib.parse.quote(
                    json.dumps({"id": self._project["id"], "name": self._project["name"]})
                ),
                domain=domain,
            )

    def trigger_workflow(self, dag_id: str, identifiers: list[str], form: dict) -> None:
        """Start a dataset workflow (delete-series) through the kaapana-backend."""
        self._authorise_project()
        payload = {
            "dag_id": dag_id,
            "workflow_name": f"bench-{dag_id}",
            "conf_data": {
                "data_form": {"identifiers": identifiers},
                "workflow_form": form,
            },
            "instance_names": [self._instance],
            "username": self.username,
        }
        response = self.session.post(
            f"{self.host}/kaapana-backend/client/workflow", json=payload, timeout=60
        )
        response.raise_for_status()


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def is_finished(run: dict) -> bool:
    return run.get("state") in TERMINAL_STATES


def trigger_time(run: dict) -> datetime | None:
    """When the run was created. Airflow renamed this field; both spellings are
    served depending on version."""
    return parse_time(run.get("logical_date") or run.get("execution_date"))


def series_uid_of(run: dict) -> str | None:
    """Kaapana's DICOM receiver puts the SeriesInstanceUID in the run conf —
    the only reliable way to tie a run back to the series that caused it."""
    return (run.get("conf") or {}).get("seriesInstanceUID")
