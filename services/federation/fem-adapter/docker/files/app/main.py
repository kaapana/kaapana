import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
import workflow_api_client as wf
from config import settings
from fastapi import FastAPI, HTTPException
from schemas import StatusResponse, SubmitRunRequest, SubmitRunResponse
from store import get_workflow_run_id, set_workflow_run_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fem-adapter")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=10.0)
    yield
    await app.state.http.aclose()


app = FastAPI(
    title="Kaapana FEM Adapter",
    description=(
        "Bridges the EUCAIM FEM-client protocol to the Kaapana workflow-api. "
        "See the service README for the (working-assumption) REST contract."
    ),
    lifespan=lifespan,
)


async def _poll_until_terminal(client: httpx.AsyncClient, workflow_run_id: int) -> dict:
    """
    Poll workflow-api for a terminal WorkflowRunStatus (Completed/Error/Canceled),
    for at most settings.POLL_TIMEOUT_SECONDS. Returns the last observed run,
    terminal or not.

    If DUMMY_ENGINE_AUTOCOMPLETE is set and the engine is the sandbox
    DummyAdapter, forces completion once the run has an external_id, so the
    local end-to-end test can observe a real terminal status synchronously
    within this single request/response cycle.
    """
    deadline = asyncio.get_event_loop().time() + settings.POLL_TIMEOUT_SECONDS
    nudged = False
    run = await wf.get_workflow_run(client, workflow_run_id)

    while True:
        if run["lifecycle_status"] in wf.TERMINAL_STATUSES:
            return run

        if (
            settings.DUMMY_ENGINE_AUTOCOMPLETE
            and not nudged
            and run.get("external_id")
        ):
            await wf.force_dummy_status(client, run["external_id"], "Completed")
            nudged = True

        if asyncio.get_event_loop().time() >= deadline:
            return run

        await asyncio.sleep(settings.POLL_INTERVAL_SECONDS)
        run = await wf.get_workflow_run(client, workflow_run_id)


@app.post("/fem/submit_run", response_model=SubmitRunResponse)
async def submit_run(body: SubmitRunRequest) -> SubmitRunResponse:
    client: httpx.AsyncClient = app.state.http

    workflow = await wf.get_or_create_workflow(client, body.task_id, body.command)
    run = await wf.create_workflow_run(client, workflow)
    set_workflow_run_id(body.execution_id, run["id"])

    run = await _poll_until_terminal(client, run["id"])

    return SubmitRunResponse(
        status=run["lifecycle_status"],
        execution_id=body.execution_id,
        workflow_run_id=run["id"],
        external_id=run.get("external_id"),
        task_id=body.task_id,
    )


@app.get("/fem/status/{execution_id}", response_model=StatusResponse)
async def get_status(execution_id: str) -> StatusResponse:
    workflow_run_id = get_workflow_run_id(execution_id)
    if workflow_run_id is None:
        raise HTTPException(status_code=404, detail=f"Unknown execution_id: {execution_id}")

    client: httpx.AsyncClient = app.state.http
    run = await wf.get_workflow_run(client, workflow_run_id)
    return StatusResponse(
        status=run["lifecycle_status"],
        execution_id=execution_id,
        workflow_run_id=workflow_run_id,
        external_id=run.get("external_id"),
    )


@app.put("/fem/cancel/{execution_id}", response_model=StatusResponse)
async def cancel(execution_id: str) -> StatusResponse:
    workflow_run_id = get_workflow_run_id(execution_id)
    if workflow_run_id is None:
        raise HTTPException(status_code=404, detail=f"Unknown execution_id: {execution_id}")

    client: httpx.AsyncClient = app.state.http
    run = await wf.cancel_workflow_run(client, workflow_run_id)
    return StatusResponse(
        status=run["lifecycle_status"],
        execution_id=execution_id,
        workflow_run_id=workflow_run_id,
        external_id=run.get("external_id"),
    )
