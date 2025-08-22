from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.dependencies import (
    get_async_db,
    get_forwarded_headers,
)
from app.adapters import get_workflow_engine, WorkflowEngineAdapter
from app import crud, schemas, models
from typing import Dict, Any
from uuid import UUID

router = APIRouter()


@router.get("/workflow-runs", response_model=List[schemas.WorkflowRun])
async def get_workflow_run_task_runs(
    title: Optional[str],
    version: Optional[int],
    db: AsyncSession = Depends(get_async_db),
):
    pass


@router.get("/workflow-runs/{workflow_run_id}", response_model=schemas.WorkflowRun)
async def get_workflow_run_task_runs(
    workflow_run_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    pass


@router.get(
    "/workflow-runs/{workflow_run_id}/task-runs", response_model=List[schemas.TaskRun]
)
async def get_workflow_run_task_runs(
    run_id: int,
    latest: bool = True,  # TODO Whether to only include the latest task-runs per task
    task_title: Optional[str] = None,  # Only include task-runs for this task title
    db: AsyncSession = Depends(get_async_db),
):
    task_runs = await crud.get_task_runs_by_workflow_run(db, workflow_run_id=run_id)
    if task_runs is None:
        raise HTTPException(
            status_code=404, detail="No task runs found for this workflow run"
        )
    return task_runs


@router.get(
    "/workflow-runs/{workflow_run_id}/tasks-runs/{task_run_id}",
    response_model=schemas.TaskRun,
)
async def get_task_run_logs(
    run_id: int,
    task_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """"""
    raise NotImplementedError


@router.get(
    "/workflow-runs/{workflow_run_id}/task-runs/{task_run_id}/logs", response_model=str
)
async def get_task_run_logs(
    workflow_run_id: int,
    task_run_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    db_workflow_run = await crud.get_workflow_runs(
        db,
        filters={"id": run_id},
        single=True,
    )
    if db_workflow_run is None:
        raise HTTPException(
            status_code=404, detail="Workflow Run not found for this workflow"
        )

    db_task_run = await crud.get_task_run_by_task_and_workflow_run(
        db, task_id=task_id, workflow_run_id=run_id
    )
    if db_task_run is None:
        raise HTTPException(
            status_code=404, detail="Task Run not found for this workflow run and task"
        )

    # Placeholder for fetching logs from workflow engine
    logs = f"Logs for Task ID {task_id} in Run ID {run_id}"
    return {"logs": logs}


@router.put(
    "/workflow-runs/{workflow_run_id}/cancel", response_model=schemas.WorkflowRun
)
async def cancel_workflow_run(
    workflow_run_id: int,
    db: AsyncSession = Depends(get_async_db),
    forwarded_headers: Dict[str, str] = Depends(get_forwarded_headers),
):
    pass


@router.put(
    "/workflow-runs/{workflow_run_id}/retry", response_model=schemas.WorkflowRun
)
async def retry_workflow_run(
    workflow_run_id: int,
    db: AsyncSession = Depends(get_async_db),
    forwarded_headers: Dict[str, str] = Depends(get_forwarded_headers),
):
    pass


@router.post(
    "/workflow-runs",
    response_model=schemas.WorkflowRun,
)
async def create_workflow_run(
    response: Response,
    workflow_run_create: schemas.WorkflowRunCreate,
    background_tasks: BackgroundTasks,
    forwarded_headers: Dict[str, str] = Depends(get_forwarded_headers),
    db: AsyncSession = Depends(get_async_db),
):

    db_workflow = await crud.get_workflows(
        db,
        filters={
            "title": title,
            "version": version,
        },
        single=True,
    )
    if db_workflow is None:
        raise HTTPException(
            status_code=404, detail="Workflow not found, not possible to create run"
        )

    workflow_run_create = schemas.WorkflowRunCreate(
        **workflow_run_create.model_dump(), title=title, version=version
    )
    db_workflow_run = await crud.create_workflow_run(
        db=db, workflow_run=workflow_run_create, workflow_id=db_workflow.id
    )

    workflow_engine = get_workflow_engine(
        workflow=schemas.Workflow(**db_workflow.__dict__)
    )
    background_tasks.add_task(
        workflow_engine.submit_workflow_run,
        workflow=db_workflow,
        workflow_run=schemas.WorkflowRun(**db_workflow_run.__dict__),
    )
    response.headers["Location"] = f"/v1/runs/{db_workflow_run.id}"
    return schemas.WorkflowRun(**db_workflow_run.__dict__)
