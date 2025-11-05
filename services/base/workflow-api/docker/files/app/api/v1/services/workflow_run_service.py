import asyncio
import logging
from typing import Any, Callable, Coroutine, List, Optional

from app import crud, models, schemas
from app.adapters import get_workflow_engine
from app.api.v1.services.errors import InternalError, NotFoundError
from app.dependencies import (  # <--- to create new session in background tasks
    get_async_db,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _run_in_background_with_retries(
    func: Callable[..., Coroutine[Any, Any, Any]],
    *args,
    max_retries: int = 3,
    delay_seconds: float = 5.0,
    **kwargs,
) -> None:
    """
    Run an async function in the background with automatic retries.

    Args:
        func: The async function to execute.
        *args: Positional arguments for the function.
        **kwargs: Keyword arguments for the function.
        max_retries: Maximum number of retries before giving up.
        delay_seconds: exponential backoff, i.e. `delay_seconds * (2 ** (attempt - 1))` is used between retries .

    Returns:
        None. Runs asynchronously and logs outcomes.
    """
    for attempt in range(1, max_retries + 1):
        try:
            # create a new session if func requires 'db'
            if "db" in kwargs:
                async for new_db in get_async_db():
                    kwargs["db"] = new_db
                    await func(*args, **kwargs)
            else:
                await func(*args, **kwargs)
            logger.debug(f"Background task {func.__name__} completed successfully.")
            return
        except Exception as e:
            logger.warning(
                f"Attempt {attempt}/{max_retries} failed for {func.__name__}: {e}"
            )
            if attempt == max_retries:
                logger.error(
                    f"All {max_retries} retries failed for background task {func.__name__}"
                )
                return
            await asyncio.sleep(
                delay_seconds * (2 ** (attempt - 1))
            )  # exponential backoff


async def get_workflow_runs(
    db: AsyncSession,
    workflow_title: Optional[str],
    workflow_version: Optional[int],
) -> List[schemas.WorkflowRun]:
    filters = {}
    if workflow_title:
        filters["workflow.title"] = workflow_title
    if workflow_version:
        filters["workflow.version"] = workflow_version

    # get workflow runs from the database
    runs: List[models.WorkflowRun] = await crud.get_workflow_runs(db, filters=filters)
    if not runs:
        logger.warning(f"No workflow runs found for {filters=}")
        return []

    res = []
    for run in runs:
        # if a run is not in a terminal state, add from db
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
            run = await crud.update_workflow_run(
                db=db,
                run_id=run.id,
                workflow_run_update=schemas.WorkflowRunUpdate(lifecycle_status=status),
            )

        # update all task runs of workflow run in the background
        task_run_updates = await engine.get_workflow_run_task_runs(run.external_id)
        for t in task_run_updates:
            asyncio.create_task(
                _run_in_background_with_retries(
                    crud.create_or_update_task_run,
                    db=None,  # session will be created inside _run_in_background_with_retries
                    task_run_update=t,
                    workflow_run_id=run.id,
                    
                )
            )
        res.append(run)
    return res


async def create_workflow_run(
    db: AsyncSession,
    workflow_run: schemas.WorkflowRunCreate,
) -> schemas.WorkflowRun:
    logger.debug(f"Creating workflow run for {workflow_run=}")

    db_workflow = await crud.get_workflows(
        db,
        filters={
            "title": workflow_run.workflow.title,
            "version": workflow_run.workflow.version,
        },
    )
    if not db_workflow:
        logger.error(f"Workflow of {workflow_run=} not found")
        raise NotFoundError("Workflow not found")
    
    # create workflow run in db
    db_workflow_run = await crud.create_workflow_run(db, workflow_run, db_workflow.id)
    if not db_workflow_run:
        logger.error(f"Failed to create workflow run for {workflow_run=}")
        raise InternalError("Failed to create workflow run")

    # submit workflow run to the workflow engine in the background
    engine = get_workflow_engine(db_workflow.workflow_engine)
    asyncio.create_task(
        _run_in_background_with_retries(
            engine.submit_workflow_run,
            workflow_run=db_workflow_run,
        )
    )

    return schemas.WorkflowRun.from_orm(db_workflow_run)


async def get_workflow_run_by_id(
    db: AsyncSession, workflow_run_id: int
) -> schemas.WorkflowRun:
    run = await crud.get_workflow_run(db, filters={"id": workflow_run_id})
    if not run:
        logger.error(f"No workflow runs found by id {workflow_run_id}")
        raise NotFoundError("Workflow run not found")

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
        raise NotFoundError("Workflow run not found")

    engine = get_workflow_engine(run.workflow.workflow_engine)
    canceled = await engine.cancel_workflow_run(run.external_id)
    if not canceled:
        logger.error(f"Failed to cancel workflow run in engine {workflow_run_id}")
        raise InternalError("Failed to cancel workflow run in engine")
    updated = await crud.update_workflow_run(
        db,
        run_id=workflow_run_id,
        workflow_run_update=schemas.WorkflowRunUpdate(
            external_id=run.external_id,
            lifecycle_status=schemas.WorkflowRunStatus.CANCELED,
        ),
    )
    return updated


async def retry_workflow_run(
    db: AsyncSession, workflow_run_id: int
) -> schemas.WorkflowRun:
    run = await crud.get_workflow_run(db, filters={"id": workflow_run_id})
    if not run:
        logger.error(f"No workflow runs found to retry {workflow_run_id}")
        raise NotFoundError("Workflow run not found")

    engine = get_workflow_engine(run.workflow.workflow_engine)
    new_run_status = await engine.retry_workflow_run(run)
    return await crud.update_workflow_run(
        db,
        run_id=workflow_run_id,
        workflow_run_update=schemas.WorkflowRunUpdate(
            lifecycle_status=new_run_status,
            external_id=run.external_id,
        ),
    )


async def get_workflow_run_task_runs(
    db: AsyncSession,
    workflow_run_id: int,
    task_title: Optional[str],  # Only include task-runs for this task title
) -> List[schemas.TaskRun]:
    workflow_run = await crud.get_workflow_run(db, filters={"id": workflow_run_id})
    if not workflow_run:
        logger.error(f"No workflow run found for id {workflow_run_id}")
        raise NotFoundError("Workflow run not found")

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
        logger.error(f"No task runs found for {workflow_run_id=} and {task_title=}")
        raise NotFoundError("No task runs found")

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
        raise NotFoundError("Task run not found")
    return schemas.TaskRun(
        id=task_run.id,
        workflow_run_id=workflow_run_id,
        external_id=task_run.external_id,
        lifecycle_status=task_run.lifecycle_status,
        task_id=task_run.task_id,
        task_title=task_run.task.title,
    )


async def get_task_run_logs(
    db: AsyncSession, workflow_run_id: int, task_run_id: int
) -> str:
    task_run = await crud.get_task_run(
        db, filters={"id": task_run_id, "workflow_run_id": workflow_run_id}
    )
    if not task_run:
        logger.error(f"Task run not found for {workflow_run_id=} and {task_run_id=}")
        raise NotFoundError("Task run not found")

    # TODO: get logs from the engine adapter
    engine = get_workflow_engine(task_run.workflow_run.workflow.workflow_engine)
    logs = await engine.get_task_run_logs(task_run.external_id)
    return logs
