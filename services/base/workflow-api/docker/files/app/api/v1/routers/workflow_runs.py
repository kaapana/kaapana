import json
import logging
import uuid
from typing import List, Optional
from urllib.parse import unquote

from app import schemas
from app.api.v1.services import workflow_run_service as service
from app.dependencies import get_async_db
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/workflow-runs", response_model=List[schemas.WorkflowRun])
async def get_workflow_runs(
    workflow_id: Optional[uuid.UUID] = None,
    workflow_increment: Optional[int] = None,
    lifecycle_status: Optional[str] = None,
    cleanup_status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_workflow_runs(
        db,
        workflow_id,
        workflow_increment,
        lifecycle_status,
        cleanup_status,
    )


@router.post("/workflow-runs", response_model=schemas.WorkflowRun, status_code=201)
async def create_workflow_run(
    request: Request,
    response: Response,
    workflow_run: schemas.WorkflowRunCreate,
    db: AsyncSession = Depends(get_async_db),
):
    project = json.loads(unquote(request.cookies["Project"]))
    project_id = project["id"]
    workflow_run_res = await service.create_workflow_run(
        db, workflow_run, project_id=project_id
    )
    response.headers["Location"] = f"/v1/workflow-runs/{workflow_run_res.id}"
    return workflow_run_res


@router.get("/workflow-runs/{workflow_run_id}", response_model=schemas.WorkflowRun)
async def get_workflow_run_by_id(
    workflow_run_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_workflow_run_by_id(db, workflow_run_id)


@router.put(
    "/workflow-runs/{workflow_run_id}/cancel", response_model=schemas.WorkflowRun
)
async def cancel_workflow_run(
    workflow_run_id: int,
    db: AsyncSession = Depends(get_async_db),
):

    return await service.cancel_workflow_run(db, workflow_run_id)


@router.put(
    "/workflow-runs/{workflow_run_id}/retry", response_model=schemas.WorkflowRun
)
async def retry_workflow_run(
    workflow_run_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.retry_workflow_run(db, workflow_run_id)


@router.get(
    "/workflow-runs/{workflow_run_id}/task-runs", response_model=List[schemas.TaskRun]
)
async def get_workflow_run_task_runs(
    workflow_run_id: int,
    task_title: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_workflow_run_task_runs(db, workflow_run_id, task_title)


@router.get(
    "/workflow-runs/{workflow_run_id}/task-runs/{task_run_id}",
    response_model=schemas.TaskRun,
)
async def get_task_run(
    workflow_run_id: int,
    task_run_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_task_run(db, workflow_run_id, task_run_id)


@router.get(
    "/workflow-runs/{workflow_run_id}/task-runs/{task_run_id}/logs",
    response_model=list[schemas.LogLine],
)
async def get_task_run_log_lines(
    workflow_run_id: int,
    task_run_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_task_run_log_lines(db, workflow_run_id, task_run_id)


@router.post("/workflow-runs/sync", status_code=204)
async def sync_workflow_runs(
    db: AsyncSession = Depends(get_async_db),
):
    """
    Trigger a manual sync of all active workflow runs with the backend engine.
    Useful for testing or recovering from missed scheduler events.
    """
    await service.sync_active_runs(db)
    return


@router.post("/workflow-runs/{workflow_run_id}/clean")
async def clean_workflow_run(
    workflow_run_id: int,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Manually trigger cleanup of a workflow run's data, regardless of policy.

    Returns:
      - 202 Accepted when cleanup is dispatched (cold start or retry from FAILED).
      - 200 OK when the run is already CLEANED (idempotent no-op).
    Errors:
      - 404 if the run does not exist.
      - 409 if a cleanup is already PENDING or RUNNING.
      - 400 if the run is not in a terminal state and has an external_id.
    """
    db_run_before = await service.get_workflow_run_by_id(db, workflow_run_id)
    if db_run_before.cleanup_status == schemas.CleanupStatus.CLEANED:
        response.status_code = 200
        return db_run_before

    db_run = await service.trigger_cleanup(db, workflow_run_id)
    response.status_code = 202
    return db_run
