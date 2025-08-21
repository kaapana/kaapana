from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.dependencies import (
    get_async_db,
    get_project,
    get_project_id,
    get_forwarded_headers,
)
from app.adapters import get_workflow_engine, WorkflowEngineAdapter
from app import crud, schemas, models
from typing import Dict, Any
from uuid import UUID

router = APIRouter()

# TODO: check which endpoints are needed, remove unused ones


# Workflow Run Endpoints
@router.get("/runs", response_model=List[schemas.WorkflowRun])
async def get_runs(
    dataset: Optional[str] = None,
    limit: Optional[int] = 100,
    skip: int = 0,
    labels: Optional[str] = None,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):
    # Build filters dict for any specific filtering needed
    # TODO: encode labels into filter
    filters = {}

    # Add dataset filter if needed
    # if dataset:
    #     filters['config'] = {'dataset': dataset}

    runs = await crud.get_workflow_runs(
        db, filters=filters, project_id=project_id, skip=skip, limit=limit
    )
    if not runs:
        raise HTTPException(status_code=404, detail="No workflow runs found")

    # TODO check if this is needed:
    for db_workflow_run in runs:
        db_workflow = await crud.get_workflows(
            db, filters={"id": db_workflow_run.workflow_id}, single=True
        )

        if db_workflow.project_id != UUID(project_id):
            raise HTTPException(
                status_code=403, detail="Workflow Run does not belong to this project"
            )

    return runs


@router.get("/runs/{run_id}", response_model=schemas.WorkflowRun)
async def get_workflow_run(
    run_id: int,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):

    # Get the specific workflow run
    db_workflow_run = await crud.get_workflow_runs(
        db,
        filters={"id": run_id},
        single=True,
    )

    if db_workflow_run is None:
        raise HTTPException(status_code=404, detail="Workflow Run not found.")
    # TODO check if this is needed:
    db_workflow = await crud.get_workflows(
        db, filters={"id": db_workflow_run.workflow_id}, single=True
    )

    if db_workflow.project_id != UUID(project_id):
        raise HTTPException(
            status_code=403, detail="Workflow Run does not belong to this project"
        )

    return db_workflow_run


@router.get("/runs/{run_id}/task-runs", response_model=List[schemas.TaskRun])
async def get_workflow_run_task_runs(
    run_id: int,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):
    task_runs = await crud.get_task_runs_by_workflow_run(db, workflow_run_id=run_id)
    if task_runs is None:
        raise HTTPException(
            status_code=404, detail="No task runs found for this workflow run"
        )
    # TODO is project check needed?
    return task_runs


@router.get("/runs/{run_id}/tasks/{task_id}/task-run", response_model=schemas.TaskRun)
async def get_task_run(
    run_id: int,
    task_id: int,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):
    # TODO is project check needed?
    db_task_run = await crud.get_task_run_by_workflow_run_and_task(
        db, task_id=task_id, workflow_run_id=run_id
    )
    if db_task_run is None:
        raise HTTPException(
            status_code=404, detail="Task Run not found for this workflow run and task"
        )
    return db_task_run


@router.get("/runs/{run_id}/tasks/{task_id}/task-run/logs")
async def get_task_run_logs(
    run_id: int,
    task_id: int,
    project_id=Depends(get_project_id),
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
    if db_workflow_run.workflow.project_id != project_id:
        raise HTTPException(
            status_code=403, detail="Workflow Run does not belong to this project"
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


@router.put("/runs/{run_id}/cancel", response_model=bool)
async def cancel_workflow_run(
    run_id: int,
    db: AsyncSession = Depends(get_async_db),
    forwarded_headers: Dict[str, str] = Depends(get_forwarded_headers),
    workflow_engine: WorkflowEngineAdapter = Depends(get_workflow_engine),
):
    success = await workflow_engine.cancel_workflow_run(
        db, forwarded_headers, workflow_run_id=run_id
    )
    return success


@router.get(
    "/workflows/{identifier}/versions/{version}/runs",
    response_model=List[schemas.WorkflowRun],
)
async def get_runs_by_workflow(
    identifier: str,
    version: int,
    limit: Optional[int] = 100,
    skip: int = 0,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):

    db_workflow = await crud.get_workflows(
        db,
        filters={
            "identifier": identifier,
            "version": version,
            "project_id": project_id,
        },
        single=True,
    )

    if db_workflow is None:
        raise HTTPException(
            status_code=404, detail=f"Workflow not found in project {project_id}"
        )

    # Get runs for this specific workflow
    runs = await crud.get_workflow_runs(
        db, filters={"workflow_id": db_workflow.id}, skip=skip, limit=limit
    )

    if not runs:
        raise HTTPException(status_code=404, detail="No runs found for this workflow")

    return runs


@router.get("/workflows/{identifier}/runs", response_model=List[schemas.WorkflowRun])
async def get_runs_by_workflow_identifier_latest_version(
    identifier: str,
    limit: Optional[int] = 100,
    skip: int = 0,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):
    # Get the latest workflow by identifier
    db_workflow = await crud.get_workflows(
        db,
        filters={"identifier": identifier, "project_id": project_id},
        order_by=models.Workflow.version.desc(),
        limit=1,
        single=True,
    )

    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Get runs for this specific workflow
    runs = await crud.get_workflow_runs(
        db, filters={"workflow_id": db_workflow.id}, skip=skip, limit=limit
    )

    if not runs:
        raise HTTPException(status_code=404, detail="No runs found for this workflow")

    return runs


@router.post(
    "/workflows/{identifier}/versions/{version}/runs",
    response_model=schemas.WorkflowRun,
)
async def create_workflow_run(
    identifier: str,
    version: int,
    workflow_run_create: schemas.WorkflowRunCreateForWorkflow,
    background_tasks: BackgroundTasks,
    forwarded_headers: Dict[str, str] = Depends(get_forwarded_headers),
    project: Dict[str, Any] = Depends(get_project),
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):

    db_workflow = await crud.get_workflows(
        db,
        filters={
            "identifier": identifier,
            "version": version,
            "project_id": project_id,
        },
        single=True,
    )
    if db_workflow is None:
        raise HTTPException(
            status_code=404, detail="Workflow not found, not possible to create run"
        )

    workflow_run_create = schemas.WorkflowRunCreate(
        **workflow_run_create.model_dump(), identifier=identifier, version=version
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

    return schemas.WorkflowRun(**db_workflow_run.__dict__)
