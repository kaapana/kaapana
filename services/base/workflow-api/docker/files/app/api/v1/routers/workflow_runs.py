import logging
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.dependencies import get_async_db
from app import schemas
from app.api.v1.services import workflow_run_service as service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/workflow-runs", response_model=List[schemas.WorkflowRun])
async def get_workflow_runs(
    workflow_title: Optional[str] = None,
    workflow_version: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_workflow_runs(db, workflow_title, workflow_version)


@router.post("/workflow-runs", response_model=schemas.WorkflowRun, status_code=201)
async def create_workflow_run(
    response: Response,
    workflow_run: schemas.WorkflowRunCreate,
    db: AsyncSession = Depends(get_async_db),
):
    workflow_run_res = await service.create_workflow_run(db, workflow_run)
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
    "/workflow-runs/{workflow_run_id}/task-runs/{task_run_id}/logs", response_model=str
)
async def get_task_run_logs(
    workflow_run_id: int,
    task_run_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_task_run_logs(db, workflow_run_id, task_run_id)
