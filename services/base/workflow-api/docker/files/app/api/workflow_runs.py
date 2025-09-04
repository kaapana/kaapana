import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.dependencies import (
    get_async_db,
    get_forwarded_headers,
)
from app.adapters import get_workflow_engine
from app import crud, schemas
from typing import Dict

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/workflow-runs", response_model=List[schemas.WorkflowRun])
async def get_workflow_runs(
    workflow_title: Optional[str] = None,
    workflow_version: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
):
    logger.debug(f"Getting workflow runs for {workflow_title=} and {workflow_version=}")
    # TODO: filter by status and created_at
    filters = {}
    if workflow_title:
        filters["workflow.title"] = workflow_title
    if workflow_version:
        filters["workflow.version"] = workflow_version
    runs = await crud.get_workflow_runs(db, filters=filters)
    logger.debug(f"Found {len(runs)} runs for {filters=}")
    return runs


@router.post("/workflow-runs", response_model=schemas.WorkflowRun, status_code=201)
async def create_workflow_run(
    response: Response,
    workflow_run: schemas.WorkflowRunCreate,
    background_tasks: BackgroundTasks,
    forwarded_headers: Dict[str, str] = Depends(get_forwarded_headers),
    db: AsyncSession = Depends(get_async_db),
):

    logger.debug(f"Creating workflow run for {workflow_run=}")

    db_workflow: schemas.Workflow = await crud.get_workflows(
        db,
        filters={
            "title": workflow_run.workflow.title,
            "version": workflow_run.workflow.version,
        },
        single=True,
    )
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    db_workflow_run = await crud.create_workflow_run(
        db=db, workflow_run=workflow_run, workflow_id=db_workflow.id
    )

    response.headers["Location"] = f"/v1/workflow-runs/{db_workflow_run.id}"
    return db_workflow_run


@router.get("/workflow-runs/{workflow_run_id}", response_model=schemas.WorkflowRun)
async def get_workflow_run_by_id(
    workflow_run_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    run = await crud.get_workflow_runs(db, filters={"id": workflow_run_id}, single=True)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run


@router.put(
    "/workflow-runs/{workflow_run_id}/cancel", response_model=schemas.WorkflowRun
)
async def cancel_workflow_run(
    workflow_run_id: int,
    db: AsyncSession = Depends(get_async_db),
    forwarded_headers: Dict[str, str] = Depends(get_forwarded_headers),
):
    run = await crud.get_workflow_runs(db, filters={"id": workflow_run_id}, single=True)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    updated = await crud.update_workflow_run(
        db,
        run_id=workflow_run_id,
        workflow_run_update=schemas.WorkflowRunUpdate(
            external_id=run.external_id,  # TODO: change to external_id once engine is supported
            lifecycle_status=schemas.LifecycleStatus.CANCELED,
        ),
    )
    return updated


@router.put(
    "/workflow-runs/{workflow_run_id}/retry", response_model=schemas.WorkflowRun
)
async def retry_workflow_run(
    workflow_run_id: int,
    db: AsyncSession = Depends(get_async_db),
    forwarded_headers: Dict[str, str] = Depends(get_forwarded_headers),
):
    run = await crud.get_workflow_runs(db, filters={"id": workflow_run_id}, single=True)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    # trigger retry in the engine adapter
    workflow_engine = get_workflow_engine(run.workflow.workflow_engine)
    new_run = await workflow_engine.retry_workflow_run(run)

    db_new_run = await crud.update_workflow_run(
        db,
        run_id=workflow_run_id,
        workflow_run_update=schemas.WorkflowRunUpdate(
            lifecycle_status=new_run.lifecycle_status,
            external_id=new_run.external_id,
        ),
    )
    return db_new_run


@router.get(
    "/workflow-runs/{workflow_run_id}/task-runs", response_model=List[schemas.TaskRun]
)
async def get_workflow_run_task_runs(
    workflow_run_id: int,
    latest: bool = True,  # TODO Whether to only include the latest task-runs per task
    task_title: Optional[str] = None,  # Only include task-runs for this task title
    db: AsyncSession = Depends(get_async_db),
):
    # TODO: support query params task_title and latest=true
    task_runs = await crud.get_task_runs_of_workflow_run(
        db, workflow_run_id=workflow_run_id, task_title=task_title, latest=latest
    )
    if not task_runs:
        logger.error(f"No task runs found for {workflow_run_id=} and {task_title=}")
        raise HTTPException(status_code=404, detail="No task runs found")
    return task_runs


@router.get(
    "/workflow-runs/{workflow_run_id}/task-runs/{task_run_id}",
    response_model=schemas.TaskRun,
)
async def get_task_run(
    workflow_run_id: int,
    task_run_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """"""
    task_run = await crud.get_task_run(
        db, workflow_run_id=workflow_run_id, task_run_id=task_run_id
    )
    if not task_run:
        logger.error(f"Task run not found for {workflow_run_id=} and {task_run_id=}")
        raise HTTPException(status_code=404, detail="Task run not found")
    return task_run


@router.get(
    "/workflow-runs/{workflow_run_id}/task-runs/{task_run_id}/logs", response_model=str
)
async def get_task_run_logs(
    workflow_run_id: int,
    task_run_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    task_run = await crud.get_task_run(
        db, workflow_run_id=workflow_run_id, task_run_id=task_run_id
    )
    if not task_run:
        raise HTTPException(status_code=404, detail="Task run not found")

    # TODO: get logs from the engine adapter
    logs = f"Logs for TaskRun {task_run_id} in WorkflowRun {workflow_run_id}"
    return logs
