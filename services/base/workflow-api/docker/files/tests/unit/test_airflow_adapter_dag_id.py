"""
Unit tests for the DAG id and DAG file of a workflow revision in the Airflow adapter.
"""

import uuid
from datetime import datetime, timezone

import pytest
from app import schemas
from app.adapters.adapters.airflow_adapter import AirflowPluginAdapter


@pytest.fixture
def adapter(tmp_path, monkeypatch) -> AirflowPluginAdapter:
    monkeypatch.setenv("AIRFLOW_DAG_FOLDER", str(tmp_path))
    return AirflowPluginAdapter()


def _revision(workflow_id: uuid.UUID, title: str, definition: str, increment: int = 1) -> schemas.WorkflowRevision:
    return schemas.WorkflowRevision(
        id=uuid.uuid4(),
        workflow_id=workflow_id,
        workflow_title=title,
        increment=increment,
        definition=definition,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("title_a,title_b", [("seg", "seg!"), ("seg", "seg"), ("my seg", "my_seg")])
async def test_workflows_with_similar_titles_get_separate_dag_files(adapter, tmp_path, title_a, title_b):
    id_a, id_b = uuid.uuid4(), uuid.uuid4()
    await adapter.submit_workflow_revision(_revision(id_a, title_a, "A {{ dag_id }}"))
    await adapter.submit_workflow_revision(_revision(id_b, title_b, "B {{ dag_id }}"))

    dag_a = adapter._resolve_dag_id(id_a, title_a, 1)
    dag_b = adapter._resolve_dag_id(id_b, title_b, 1)
    assert dag_a == f"{id_a}_inc1"
    assert dag_b == f"{id_b}_inc1"
    assert (tmp_path / f"{dag_a}.py").read_text() == f"A {dag_a}"
    assert (tmp_path / f"{dag_b}.py").read_text() == f"B {dag_b}"


@pytest.mark.asyncio
async def test_dag_id_does_not_change_when_title_changes(adapter):
    workflow_id = uuid.uuid4()
    await adapter.submit_workflow_revision(_revision(workflow_id, "seg", "A"))

    assert adapter._resolve_dag_id(workflow_id, "renamed", 1) == f"{workflow_id}_inc1"


@pytest.mark.asyncio
async def test_submit_refuses_to_replace_a_different_dag_file(adapter, tmp_path):
    workflow_id = uuid.uuid4()
    (tmp_path / f"{workflow_id}_inc1.py").write_text("other")

    with pytest.raises(RuntimeError):
        await adapter.submit_workflow_revision(_revision(workflow_id, "seg", "new"))
    assert (tmp_path / f"{workflow_id}_inc1.py").read_text() == "other"


@pytest.mark.asyncio
async def test_submit_same_revision_twice_is_allowed(adapter, tmp_path):
    revision = _revision(uuid.uuid4(), "seg", "A")
    await adapter.submit_workflow_revision(revision)
    await adapter.submit_workflow_revision(revision)

    assert (tmp_path / f"{revision.workflow_id}_inc1.py").read_text() == "A"


def test_existing_revision_keeps_its_title_based_dag_id(adapter, tmp_path):
    workflow_id = uuid.uuid4()
    (tmp_path / "Lung_Seg_v2_inc3.py").write_text("legacy")

    assert adapter._resolve_dag_id(workflow_id, "Lung Seg (v2)", 3) == "Lung_Seg_v2_inc3"


def test_new_format_wins_over_title_based_dag_file(adapter, tmp_path):
    workflow_id = uuid.uuid4()
    (tmp_path / "seg_inc1.py").write_text("legacy")
    (tmp_path / f"{workflow_id}_inc1.py").write_text("new")

    assert adapter._resolve_dag_id(workflow_id, "seg", 1) == f"{workflow_id}_inc1"


@pytest.mark.asyncio
async def test_run_uses_dag_id_of_its_workflow(adapter, monkeypatch):
    workflow_id = uuid.uuid4()
    await adapter.submit_workflow_revision(_revision(workflow_id, "seg", "A"))
    calls = []

    async def _request(method, endpoint, json={}, accepted_content_types=("application/json",)):
        calls.append((method, endpoint))
        if endpoint.endswith("/tasks"):
            return {"tasks": []}
        return {"dag_run_id": "manual__1"}

    async def _fetch_project(project_id):
        return {}

    monkeypatch.setattr(adapter, "_request", _request)
    monkeypatch.setattr(adapter, "_fetch_project", _fetch_project)
    run = schemas.WorkflowRun.model_construct(
        workflow=schemas.WorkflowRef(id=workflow_id, title="seg", increment=1),
        workflow_parameters=[],
    )

    update = await adapter.submit_workflow_run(run, project_id="p")

    assert ("POST", f"/dags/{workflow_id}_inc1/dagRuns") in calls
    assert update.external_id == f"{workflow_id}_inc1::manual__1"
