"""The trigger endpoint retries a DAG run whose run id or execution date is taken.

Parallel triggers of one DAG can collide on either unique key of Airflow's dag_run
table; the endpoint must retry with fresh values and answer 409 only when every
attempt collides, keeping the success response that callers parse.
"""

import importlib.util
import itertools
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from airflow.exceptions import DagNotFound, DagRunAlreadyExists
from flask import Flask
from sqlalchemy.exc import IntegrityError

BLUEPRINTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "data-processing/kaapana-plugin/extension/docker/files/plugin/kaapana/blueprints"
)
DAG_ID = "service-process-incoming-dcm"


@pytest.fixture
def api(monkeypatch):
    # Loaded per test by file path: the package __init__ needs flask_admin, the real
    # globals create an Airflow DB on import, and the operator tests replace
    # kaapana.blueprints in sys.modules with a MagicMock.
    blueprints = types.ModuleType("kaapana.blueprints")
    blueprints.__path__ = [str(BLUEPRINTS_DIR)]
    global_variables = types.ModuleType("kaapana.blueprints.kaapana_global_variables")
    global_variables.SERVICES_NAMESPACE = "services"
    stubs = {
        "kaapanapy": MagicMock(),
        "kaapanapy.helper": MagicMock(),
        "kaapana.blueprints": blueprints,
        "kaapana.blueprints.kaapana_global_variables": global_variables,
    }
    for name, module in stubs.items():
        monkeypatch.setitem(sys.modules, name, module)
    for name in ("json_schema_templates", "kaapana_utils", "kaapana_api"):
        full_name = f"kaapana.blueprints.{name}"
        spec = importlib.util.spec_from_file_location(
            full_name, BLUEPRINTS_DIR / f"{name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, full_name, module)
        spec.loader.exec_module(module)
    return sys.modules["kaapana.blueprints.kaapana_api"]


@pytest.fixture
def client(api):
    app = Flask(__name__)
    app.register_blueprint(api.kaapanaApi)
    return app.test_client()


@pytest.fixture
def sleeps(api, monkeypatch):
    calls = []
    monkeypatch.setattr(api.time, "sleep", calls.append)
    return calls


@pytest.fixture
def run_ids(api, monkeypatch):
    counter = itertools.count()
    monkeypatch.setattr(
        api, "generate_run_id", lambda dag_id: f"{dag_id}-{next(counter)}"
    )


def fake_trigger(api, monkeypatch, outcomes):
    """Replace Airflow's trigger; each call raises or succeeds per `outcomes`."""
    calls = []

    def trigger(dag_id, run_id, conf, execution_date, replace_microseconds=True):
        calls.append({"run_id": run_id, "execution_date": execution_date})
        outcome = outcomes[min(len(calls), len(outcomes)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return types.SimpleNamespace(dag_id=dag_id, run_id=run_id)

    monkeypatch.setattr(api, "trigger", trigger)
    return calls


def run_id_taken():
    return IntegrityError(
        "INSERT INTO dag_run ...",
        {},
        Exception("duplicate key value violates unique constraint"),
    )


def execution_date_taken():
    return DagRunAlreadyExists(
        dag_run=types.SimpleNamespace(dag_id=DAG_ID),
        execution_date=datetime.now(timezone.utc),
        run_id="taken",
    )


def post(client):
    return client.post(f"/kaapana/api/trigger/{DAG_ID}", json={"conf": {"a": 1}})


@pytest.mark.usefixtures("run_ids")
def test_collisions_are_retried_with_fresh_values(api, client, sleeps, monkeypatch):
    calls = fake_trigger(
        api, monkeypatch, [run_id_taken(), execution_date_taken(), "success"]
    )

    response = post(client)

    assert response.status_code == 200
    run_ids = [call["run_id"] for call in calls]
    assert len(set(run_ids)) == 3
    # None lets Airflow take a fresh utcnow() as execution date on every attempt.
    assert all(call["execution_date"] is None for call in calls)
    assert response.get_json() == {
        "message": [
            f"{DAG_ID} created!",
            {"dag_id": DAG_ID, "run_id": run_ids[-1]},
        ]
    }
    assert len(sleeps) == 2


@pytest.mark.usefixtures("run_ids")
def test_conflict_after_every_attempt_collides(api, client, sleeps, monkeypatch):
    calls = fake_trigger(api, monkeypatch, [run_id_taken()])

    response = post(client)

    assert response.status_code == 409
    assert "error" in response.get_json()
    assert len(calls) == api.TRIGGER_ATTEMPTS == 5
    assert len(sleeps) == 4


@pytest.mark.usefixtures("run_ids")
def test_other_airflow_errors_are_not_retried(api, client, sleeps, monkeypatch):
    calls = fake_trigger(api, monkeypatch, [DagNotFound("Dag id missing not found")])

    response = post(client)

    assert response.status_code == 404
    assert response.get_json() == {"error": "Dag id missing not found"}
    assert len(calls) == 1
    assert sleeps == []
