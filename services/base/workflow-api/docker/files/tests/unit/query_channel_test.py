"""workflow-api is Data-API-agnostic: a `query` channel is just a parameter whose
value (a JSON entity-ID list the frontend resolved) flows to the task env like any
other parameter. There is no server-side freeze and no Data API client."""

import inspect
import json
from datetime import datetime, timezone

import pytest

from app import schemas
from app.adapters.adapters.airflow_adapter import AirflowPluginAdapter


def _query_ui_form(**overrides) -> dict:
    base = {"type": "query", "title": "Channel", "description": "d", "required": True}
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_query_channel_value_flows_to_task_env_like_any_param(monkeypatch):
    adapter = AirflowPluginAdapter()
    captured: dict = {}

    async def _fake_tasks(workflow):
        return []

    async def _fake_request(method, path, json=None):
        captured["payload"] = json
        return {"dag_run_id": "run-123"}

    monkeypatch.setattr(adapter, "get_workflow_tasks", _fake_tasks)
    monkeypatch.setattr(adapter, "_request", _fake_request)
    monkeypatch.setattr(
        adapter, "_get_dag_id_from_workflow", lambda wf: "dag-x", raising=True
    )

    run = schemas.WorkflowRun(
        id=1,
        external_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        lifecycle_status=schemas.WorkflowRunStatus.CREATED,
        workflow=schemas.WorkflowRef(title="w", version=1),
        workflow_parameters=[
            # A query channel: the FE resolved the selection to this JSON ID list.
            schemas.WorkflowParameter(
                task_title="download_model",
                env_variable_name="INPUT_ENTITY_IDS",
                ui_form=_query_ui_form(default=json.dumps(["e1", "e2"])),
            ),
            # An ordinary scalar param flows the same way.
            schemas.WorkflowParameter(
                task_title="train",
                env_variable_name="EPOCHS",
                ui_form={
                    "type": "int",
                    "title": "Epochs",
                    "description": "d",
                    "default": 5,
                },
            ),
        ],
    )

    await adapter.submit_workflow_run(run, project_id="proj-1")

    task_form = captured["payload"]["conf"]["task_form"]
    dl_env = task_form["download_model"]["env"]
    matching = [e for e in dl_env if e["name"] == "INPUT_ENTITY_IDS"]
    assert len(matching) == 1
    # The frozen ID list travels verbatim as the env value (JSON string).
    assert matching[0]["value"] == json.dumps(["e1", "e2"])

    train_env = task_form["train"]["env"]
    assert any(e["name"] == "EPOCHS" and e["value"] == 5 for e in train_env)


def test_query_ui_form_cardinality_defaults_to_multiple():
    form = schemas.QueryUIForm(**_query_ui_form())
    assert form.cardinality == "multiple"


def test_query_ui_form_accepts_single_cardinality():
    form = schemas.QueryUIForm(**_query_ui_form(cardinality="single"))
    assert form.cardinality == "single"


def test_query_ui_form_rejects_unknown_cardinality():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        schemas.QueryUIForm(**_query_ui_form(cardinality="some"))


def test_query_ui_form_display_fields_default_empty():
    form = schemas.QueryUIForm(**_query_ui_form())
    assert form.display_fields == []


def test_query_ui_form_accepts_display_fields():
    fields = ["metadata.model.name", "metadata.provenance.created_at"]
    form = schemas.QueryUIForm(**_query_ui_form(display_fields=fields))
    assert form.display_fields == fields


def test_workflow_run_service_has_no_data_api_coupling():
    """The Data API freeze + client were removed entirely."""
    from app.api.v1.services import workflow_run_service as wrs

    src = inspect.getsource(wrs)
    assert "DataClient" not in src
    assert "data_api" not in src
    assert "DATA_API_URL" not in src
    assert not hasattr(wrs, "_freeze_input_channels")
    assert not hasattr(wrs, "_effective_where")
