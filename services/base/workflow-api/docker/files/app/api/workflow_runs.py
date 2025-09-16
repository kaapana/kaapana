import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List, Optional
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
    background_tasks: BackgroundTasks,
    workflow_title: Optional[str] = None,
    workflow_version: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
):
    logger.debug(f"Getting workflow runs for {workflow_title=} and {workflow_version=}")
    # TODO: add filtering by status and created_at
    filters = {}
    if workflow_title:
        filters["workflow.title"] = workflow_title
    if workflow_version:
        filters["workflow.version"] = workflow_version

    # get workflow runs from the database
    runs = await crud.get_workflow_runs(db, filters=filters, single=False)
    if not runs:
        raise HTTPException(status_code=404, detail="No workflow runs found")

    res = []
    # get all run statuses from the engine adapter
    for run in runs:
        # add from db directly, if a run is not already completed
        if run.lifecycle_status in [
            schemas.WorkflowRunStatus.COMPLETED,
            schemas.WorkflowRunStatus.ERROR,
            schemas.WorkflowRunStatus.CANCELED,
        ]:
            res.append(run)
            continue

        # get status from the engine
        engine = get_workflow_engine(run.workflow.workflow_engine)
        status = await engine.get_workflow_run_status(
            workflow_run_external_id=run.external_id
        )
        if status != run.lifecycle_status:
            updated_run: schemas.WorkflowRun = await crud.update_workflow_run(
                db=db,
                run_id=run.id,
                workflow_run_update=schemas.WorkflowRunUpdate(lifecycle_status=status),
            )
            run = updated_run
        # update all task runs of workflow run in the background
        task_run_updates = await engine.get_workflow_run_task_runs(run.external_id)
        for task_run_update in task_run_updates:
            background_tasks.add_task(
                crud.create_or_update_task_run, db, task_run_update, run.id
            )
        res.append(run)
    return res


@router.post("/workflow-runs", response_model=schemas.WorkflowRun, status_code=201)
async def create_workflow_run(
    response: Response,
    workflow_run: schemas.WorkflowRunCreate,
    background_tasks: BackgroundTasks,
    forwarded_headers: Dict[str, str] = Depends(get_forwarded_headers),
    db: AsyncSession = Depends(get_async_db),
):
    logger.debug(f"Creating workflow run for {workflow_run=}")

    # get workflow of workflow run from the database
    db_workflow = await crud.get_workflows(
        db,
        filters={
            "title": workflow_run.workflow.title,
            "version": workflow_run.workflow.version,
        },
        single=True,
    )
    if not db_workflow:
        logger.error(f"Workflow of {workflow_run=} not found")
        raise HTTPException(status_code=404, detail="Workflow not found")

    # create workflow run in the database
    db_workflow_run = await crud.create_workflow_run(
        db=db, workflow_run=workflow_run, workflow_id=db_workflow.id
    )
    if not db_workflow_run:
        logger.error(f"Failed to create workflow run for {workflow_run=}")
        raise HTTPException(status_code=400, detail="Failed to create workflow run")
    response.headers["Location"] = f"/v1/workflow-runs/{db_workflow_run.id}"

    # create workflow run in the engine in the background
    engine = get_workflow_engine(db_workflow.workflow_engine)
    background_tasks.add_task(
        engine.submit_workflow_run,
        workflow_run=db_workflow_run,
    )

    return db_workflow_run


@router.get("/workflow-runs/{workflow_run_id}", response_model=schemas.WorkflowRun)
async def get_workflow_run_by_id(
    workflow_run_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    run = await crud.get_workflow_runs(db, filters={"id": workflow_run_id}, single=True)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    # TODO: add a query parameter to limit engine calls so that it is not called on every request
    engine = get_workflow_engine(run.workflow.workflow_engine)
    status = await engine.get_workflow_run_status(
        workflow_run_external_id=run.external_id
    )
    if status != run.lifecycle_status:
        updated_run = await crud.update_workflow_run(
            db=db,
            run_id=workflow_run_id,
            workflow_run_update=schemas.WorkflowRunUpdate(lifecycle_status=status),
        )
        run = updated_run

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

    engine = get_workflow_engine(run.workflow.workflow_engine)
    canceled = await engine.cancel_workflow_run(run.external_id)
    if not canceled:
        raise HTTPException(
            status_code=400, detail="Failed to cancel workflow run in engine"
        )

    updated = await crud.update_workflow_run(
        db,
        run_id=workflow_run_id,
        workflow_run_update=schemas.WorkflowRunUpdate(
            external_id=run.external_id,
            lifecycle_status=schemas.WorkflowRunStatus.CANCELED,
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
    task_title: Optional[str] = None,  # Only include task-runs for this task title
    db: AsyncSession = Depends(get_async_db),
):
    workflow_run = await crud.get_workflow_runs(
        db, filters={"id": workflow_run_id}, single=True
    )
    # check if the workflow run is completed
    if workflow_run.lifecycle_status not in [
        schemas.WorkflowRunStatus.COMPLETED,
        schemas.WorkflowRunStatus.ERROR,
        schemas.WorkflowRunStatus.CANCELED,
    ]:
        # get task runs from the engine adapter
        workflow_engine = get_workflow_engine(workflow_run.workflow.workflow_engine)

        task_run_updates = await workflow_engine.get_workflow_run_task_runs(
            workflow_run_external_id=workflow_run.external_id
        )
        logger.info(f"Got {len(task_run_updates)} task runs from the engine")

        # update task runs in the database and return the list
        res_task_runs = []
        for task_run_update in task_run_updates:
            db_tr = await crud.create_or_update_task_run(
                db, task_run_update=task_run_update, workflow_run_id=workflow_run_id
            )
            res_task_runs.append(db_tr)

    # TODO: support query params task_title and latest=true
    filters: dict[str, Any] = {
        "workflow_run_id": workflow_run_id,
    }
    if task_title:
        filters["task.title"] = task_title

    db_task_runs = await crud.get_task_runs(
        db,
        filters=filters,
    )
    if not db_task_runs:
        logger.error(f"No task runs found for {workflow_run_id=} and {task_title=}")
        raise HTTPException(status_code=404, detail="No task runs found")

    # cast task runs as
    res = []
    for db_task_run in db_task_runs:
        encoded_task_run = jsonable_encoder(db_task_run)
        res.append(
            schemas.TaskRun(
                id=encoded_task_run["id"],
                workflow_run_id=workflow_run_id,
                external_id=encoded_task_run["external_id"],
                lifecycle_status=encoded_task_run["lifecycle_status"],
                task_id=encoded_task_run["task_id"],
                task_title=encoded_task_run["task"]["title"],
            )
        )

    return res


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
