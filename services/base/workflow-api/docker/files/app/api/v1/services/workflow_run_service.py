import logging
from typing import Any, List, Optional

from app import crud, models, schemas
from app.adapters import get_workflow_engine
from fastapi import BackgroundTasks, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_workflow_runs(
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    workflow_title: Optional[str],
    workflow_version: Optional[int],
) -> List[schemas.WorkflowRun]:
    # TODO: add filtering by status and created_at
    filters: dict[str, Any] = {}
    if workflow_title:
        filters["workflow.title"] = workflow_title
    if workflow_version:
        filters["workflow.version"] = workflow_version

    # get workflow runs from the database
    logger.info(f"Getting workflow runs with filters: {filters}")
    runs: List[models.WorkflowRun] = await crud.get_workflow_runs(db, filters=filters)
    if not runs:
        logger.info(f"No workflow runs found for {filters=}")
        return []

    # get all run statuses from the engine adapter
    res = []
    for run in runs:
        # if a run is in a terminal state, keep DB value
        if run.lifecycle_status in [
            schemas.WorkflowRunStatus.COMPLETED,
            schemas.WorkflowRunStatus.ERROR,
            schemas.WorkflowRunStatus.CANCELED,
        ]:
            res.append(run)
            continue

        # get status from the engine
        engine = get_workflow_engine(run.workflow.workflow_engine)
        status = await engine.get_workflow_run_status(run.external_id)

        if status != run.lifecycle_status:
            logger.info(
                f"Updating workflow run {run.id} status from {run.lifecycle_status} to {status}"
            )
            run = await crud.update_workflow_run(
                db=db,
                run_id=run.id,
                workflow_run_update=schemas.WorkflowRunUpdate(lifecycle_status=status),
            )

        # update all task runs of workflow run in the background
        task_run_updates = await engine.get_workflow_run_task_runs(run.external_id)
        for t in task_run_updates:
            background_tasks.add_task(crud.create_or_update_task_run, db, t, run.id)

        res.append(run)

    return res


async def create_workflow_run(
    db: AsyncSession,
    response: Response,
    workflow_run: schemas.WorkflowRunCreate,
    background_tasks: BackgroundTasks,
) -> schemas.WorkflowRun:
    logger.debug(f"Creating workflow run for {workflow_run=}")

    # get workflow of workflow run from db
    db_workflow = await crud.get_workflow(
        db,
        filters={
            "title": workflow_run.workflow.title,
            "version": workflow_run.workflow.version,
        },
    )
    if not db_workflow:
        logger.error(f"Workflow of {workflow_run=} not found")
        raise HTTPException(status_code=404, detail="Workflow not found")

    # create workflow run in db
    db_workflow_run = await crud.create_workflow_run(db, workflow_run, db_workflow.id)
    if not db_workflow_run:
        logger.error(f"Failed to create workflow run for {workflow_run=}")
        raise HTTPException(status_code=400, detail="Failed to create workflow run")

    # submit workflow run to the workflow engine in the background
    engine = get_workflow_engine(db_workflow.workflow_engine)
    background_tasks.add_task(engine.submit_workflow_run, workflow_run=db_workflow_run)
    return db_workflow_run


async def get_workflow_run_by_id(
    db: AsyncSession, workflow_run_id: int
) -> schemas.WorkflowRun:
    run = await crud.get_workflow_run(db, filters={"id": workflow_run_id})
    if not run:
        logger.error(f"No workflow runs found by id {workflow_run_id}")
        raise HTTPException(status_code=404, detail="Workflow run not found")

    # TODO: add a query parameter to limit engine calls so that it is not called on every request
    engine = get_workflow_engine(run.workflow.workflow_engine)
    status = await engine.get_workflow_run_status(run.external_id)
    if status != run.lifecycle_status:
        run = await crud.update_workflow_run(
            db=db,
            run_id=workflow_run_id,
            workflow_run_update=schemas.WorkflowRunUpdate(lifecycle_status=status),
        )
    return run


async def cancel_workflow_run(
    db: AsyncSession, workflow_run_id: int
) -> schemas.WorkflowRun:
    run = await crud.get_workflow_run(db, filters={"id": workflow_run_id})
    if not run:
        logger.error(f"No workflow runs found to cancel {workflow_run_id}")
        raise HTTPException(status_code=404, detail="Workflow run not found")

    engine = get_workflow_engine(run.workflow.workflow_engine)
    new_status = await engine.cancel_workflow_run(run)
    
    updated = await crud.update_workflow_run(
        db,
        run_id=workflow_run_id,
        workflow_run_update=schemas.WorkflowRunUpdate(
            lifecycle_status=new_status,
        ),
    )
    return updated


async def retry_workflow_run(
    db: AsyncSession, workflow_run_id: int
) -> schemas.WorkflowRun:
    run = await crud.get_workflow_run(db, filters={"id": workflow_run_id})
    if not run:
        logger.error(f"No workflow runs found to retry {workflow_run_id}")
        raise HTTPException(status_code=404, detail="Workflow run not found")

    # trigger retry in the engine adapter
    engine = get_workflow_engine(run.workflow.workflow_engine)
    new_status = await engine.retry_workflow_run(run.external_id)
    return await crud.update_workflow_run(
        db,
        run_id=workflow_run_id,
        workflow_run_update=schemas.WorkflowRunUpdate(
            lifecycle_status=new_status,
        ),
    )


async def get_workflow_run_task_runs(
    db: AsyncSession,
    workflow_run_id: int,
    task_title: Optional[str],  # Only include task-runs for this task title
) -> List[schemas.TaskRun]:
    workflow_run = await crud.get_workflow_run(db, filters={"id": workflow_run_id})

    # get task runs from the engine adapter if the workflow run is not in a terminal state
    if workflow_run.lifecycle_status not in [
        schemas.WorkflowRunStatus.COMPLETED,
        schemas.WorkflowRunStatus.ERROR,
        schemas.WorkflowRunStatus.CANCELED,
    ]:
        engine = get_workflow_engine(workflow_run.workflow.workflow_engine)
        task_run_updates = await engine.get_workflow_run_task_runs(
            workflow_run.external_id
        )
        logger.info(f"Got {len(task_run_updates)} task runs from the engine")

        for t in task_run_updates:
            await crud.create_or_update_task_run(db, t, workflow_run_id)

    # TODO: support query params task_title and latest=true
    filters: dict[str, Any] = {"workflow_run_id": workflow_run_id}
    if task_title:
        filters["task.title"] = task_title

    # get task runs
    db_task_runs = await crud.get_task_runs(db, filters=filters)
    if not db_task_runs:
        logger.info(f"No task runs found for {workflow_run_id=} and {task_title=}")
        return []

    return [
        schemas.TaskRun(
            id=tr.id,
            workflow_run_id=workflow_run_id,
            external_id=tr.external_id,
            lifecycle_status=tr.lifecycle_status,
            task_id=tr.task_id,
            task_title=tr.task.title,
        )
        for tr in db_task_runs
    ]


async def get_task_run(
    db: AsyncSession, workflow_run_id: int, task_run_id: int
) -> schemas.TaskRun:
    task_run = await crud.get_task_run(
        db, filters={"id": task_run_id, "workflow_run_id": workflow_run_id}
    )
    if not task_run:
        logger.error(f"Task run not found for {workflow_run_id=} and {task_run_id=}")
        raise HTTPException(status_code=404, detail="Task run not found")
    return task_run


async def get_task_run_logs(
    db: AsyncSession, workflow_run_id: int, task_run_id: int
) -> str:
    task_run = await crud.get_task_run(
        db, filters={"id": task_run_id, "workflow_run_id": workflow_run_id}
    )
    if not task_run:
        logger.error(f"Task run not found for {workflow_run_id=} and {task_run_id=}")
        raise HTTPException(status_code=404, detail="Task run not found")

    # TODO: get logs from the engine adapter
    engine = get_workflow_engine(task_run.workflow_run.workflow.workflow_engine)
    logs = await engine.get_task_run_logs(task_run.external_id)
    return logs
