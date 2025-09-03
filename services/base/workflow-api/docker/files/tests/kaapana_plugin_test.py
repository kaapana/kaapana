import pytest
import httpx
from app import schemas
import time


@pytest.mark.asyncio
async def test_workflow_run(client: httpx.AsyncClient):
    workflow_create = schemas.WorkflowCreate(
        title="collect-metadata",
        definition="A test workflow",
        labels=[
            schemas.Label(key="kaapana.builtin.workflow_engine", value="kaapana-plugin")
        ],
        workflow_engine="kaapana-plugin",
    )
    response = await client.post("/workflows", json=workflow_create.model_dump())
    response.raise_for_status()
    workflow = schemas.Workflow(**response.json())
    assert workflow.title == "collect-metadata"

    ### Trigger a workflow run
    config = {
        "data_form": {
            "identifiers": ["1.3.12.2.1107.5.1.4.73104.30000020081307523376400012735"],
            "dataset_name": "phantom",
        },
        "workflow_form": {
            "single_execution": False,
        },
        "project_form": {
            "name": "admin",
            "description": "Initial admin project",
            "kubernetes_namespace": "project-admin",
            "s3_bucket": "project-admin",
            "opensearch_index": "project_admin",
        },
    }
    workflow_run_create = schemas.WorkflowRunCreate(
        workflow=schemas.WorkflowRef(title=workflow.title, version=workflow.version),
        config=config,
    )

    response = await client.post("workflow-runs", json=workflow_run_create.model_dump())
    response.raise_for_status()

    created_wf_run = schemas.WorkflowRun(**response.json())
    status = created_wf_run.lifecycle_status
    timeout = 300
    start_time = time.time()
    while status != schemas.LifecycleStatus.COMPLETED:
        response = await client.get(f"workflow-runs/{created_wf_run.id}")
        wf_run = schemas.WorkflowRun(**response.json())
        status = wf_run.lifecycle_status
        print(status)

        assert status not in [schemas.LifecycleStatus.ERROR]
        assert abs(start_time - time.time()) <= timeout
        time.sleep(5)
