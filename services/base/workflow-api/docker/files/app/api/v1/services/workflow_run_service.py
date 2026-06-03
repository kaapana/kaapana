import asyncio
import logging
import uuid
from typing import Any, List, Optional

from app import crud, models, schemas
from app.adapters import WorkflowEngineAdapter, get_workflow_engine
from app.api.v1.services.errors import InternalError, NotFoundError
from app.api.v1.services.utils import run_in_background_with_retries
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _workflow_run_to_schema(db_run: models.WorkflowRun) -> schemas.WorkflowRun:
    """Map `WorkflowRun` row into the `WorkflowRun` response schema."""
    rev = db_run.workflow_revision
    workflow_ref = schemas.WorkflowRef(
        id=rev.workflow_id, title=rev.workflow.title, increment=rev.increment
    )
    task_runs = [
        schemas.TaskRun(
            id=tr.id,
            workflow_run_id=db_run.id,
            external_id=tr.external_id,
            lifecycle_status=tr.lifecycle_status,
            task_id=tr.task_id,
            task_title=tr.task.title if tr.task else "",
        )
        for tr in (db_run.task_runs or [])
    ]
    return schemas.WorkflowRun(
        id=db_run.id,
        workflow=workflow_ref,
        labels=[schemas.Label(key=l.key, value=l.value) for l in (db_run.labels or [])],
        workflow_parameters=db_run.workflow_parameters or [],
        external_id=db_run.external_id,
        created_at=db_run.created_at,
        updated_at=db_run.updated_at,
        lifecycle_status=db_run.lifecycle_status,
        task_runs=task_runs,
    )


async def get_workflow_runs(
    db: AsyncSession,
    workflow_id: Optional[uuid.UUID],
    workflow_increment: Optional[int],
    lifecycle_status: Optional[str] = None,
) -> List[schemas.WorkflowRun]:
    """List workflow runs, optionally filtered by source workflow id and/or revision increment."""
    filters: dict[str, Any] = {}
    if workflow_id:
        filters["workflow_revision.workflow_id"] = workflow_id
    if workflow_increment:
        filters["workflow_revision.increment"] = workflow_increment
    if lifecycle_status:
        filters["lifecycle_status"] = schemas.WorkflowRunStatus[lifecycle_status]

    db_runs: List[models.WorkflowRun] = await crud.get_workflow_runs(
        db, filters=filters
    )
    if not db_runs:
        logger.warning(f"No workflow runs found for {filters=}")
        return []

    res: List[models.WorkflowRun] = []
    for db_run in db_runs:
        if db_run.lifecycle_status in [
            schemas.WorkflowRunStatus.COMPLETED,
            schemas.WorkflowRunStatus.ERROR,
            schemas.WorkflowRunStatus.CANCELED,
            schemas.WorkflowRunStatus.CREATED,
        ]:
            res.append(db_run)
            continue

        assert (
            db_run.external_id is not None
        ), "external_id must exist for non-CREATED runs"

        engine = get_workflow_engine(db_run.workflow_revision.workflow.workflow_engine)
        status = await engine.get_workflow_run_status(db_run.external_id)
        if status != db_run.lifecycle_status:
            await crud.update_workflow_run(
                db=db,
                run_id=db_run.id,
                workflow_run_update=schemas.WorkflowRunUpdate(lifecycle_status=status),
            )

        task_run_updates = await engine.get_workflow_run_task_runs(db_run.external_id)
        for t in task_run_updates:
            asyncio.create_task(
                run_in_background_with_retries(
                    crud.create_or_update_task_run,
                    db=None,
                    task_run_update=t,
                    workflow_run_id=db_run.id,
                )
            )
        res.append(db_run)
    return [_workflow_run_to_schema(r) for r in res]


async def create_workflow_run(
    db: AsyncSession,
    workflow_run: schemas.WorkflowRunCreate,
    project_id: str,
) -> schemas.WorkflowRun:
    """
    Create a workflow run for a specific revision and submit it to the engine in the background.
    Resolves the `(workflow_id, increment)` reference on the incoming `WorkflowRunCreate` to the matching `WorkflowRevision`.
    """
    logger.debug(f"Creating workflow run for {workflow_run=}")

    db_revision = await crud.get_workflow_revision(
        db,
        workflow_id=workflow_run.workflow.id,
        increment=workflow_run.workflow.increment,
    )
    if not db_revision or db_revision.workflow.removed:
        logger.error(f"Workflow revision of {workflow_run=} not found")
        raise NotFoundError("Workflow revision not found")

    db_workflow_run = await crud.create_workflow_run(db, workflow_run, db_revision.id)
    if not db_workflow_run:
        logger.error(f"Failed to create workflow run for {workflow_run=}")
        raise InternalError("Failed to create workflow run")

    # eager-reload to ensure the workflow_revision relationship is loaded for serialization
    await db.refresh(db_workflow_run, attribute_names=["workflow_revision"])

    engine = get_workflow_engine(db_revision.workflow.workflow_engine)
    asyncio.create_task(
        run_in_background_with_retries(
            _submit_workflow_run_to_engine,
            db=db,
            workflow_run=_workflow_run_to_schema(db_workflow_run),
            workflow_engine=engine,
            project_id=project_id,
        )
    )

    return _workflow_run_to_schema(db_workflow_run)


async def get_workflow_run_by_id(
    db: AsyncSession, workflow_run_id: int
) -> schemas.WorkflowRun:
    """
    Get a single workflow run by id. 
    For non-terminal runs, sync lifecycle status from the engine first so the returned schema reflects current state.
    """
    db_run = await crud.get_workflow_run(db, filters={"id": workflow_run_id})
    if not db_run:
        logger.error(f"No workflow runs found by id {workflow_run_id}")
        raise NotFoundError("Workflow run not found")

    # if a run is in a terminal state, no need to sync with engine, as well as if it was just created and not yet recognized by engine
    if db_run.lifecycle_status in [
        schemas.WorkflowRunStatus.COMPLETED,
        schemas.WorkflowRunStatus.ERROR,
        schemas.WorkflowRunStatus.CANCELED,
        schemas.WorkflowRunStatus.CREATED,
    ]:
        return _workflow_run_to_schema(db_run)

    assert db_run.external_id is not None, "external_id must exist for non-CREATED runs"

    engine = get_workflow_engine(db_run.workflow_revision.workflow.workflow_engine)
    status = await engine.get_workflow_run_status(db_run.external_id)
    if status != db_run.lifecycle_status:
        db_run = await crud.update_workflow_run(
            db=db,
            run_id=workflow_run_id,
            workflow_run_update=schemas.WorkflowRunUpdate(lifecycle_status=status),
        )
    return _workflow_run_to_schema(db_run)


async def cancel_workflow_run(
    db: AsyncSession, workflow_run_id: int
) -> schemas.WorkflowRun:
    """
    Cancel a workflow run in the engine and persist the CANCELED state.
    Returns the existing schema if the run is already in a terminal state or still in CREATED.
    """
    db_run = await crud.get_workflow_run(db, filters={"id": workflow_run_id})
    if not db_run:
        logger.error(f"No workflow runs found to cancel {workflow_run_id}")
        raise NotFoundError("Workflow run not found")

    if db_run.lifecycle_status in [
        schemas.WorkflowRunStatus.COMPLETED,
        schemas.WorkflowRunStatus.ERROR,
        schemas.WorkflowRunStatus.CANCELED,
        schemas.WorkflowRunStatus.CREATED,
    ]:
        return _workflow_run_to_schema(db_run)

    assert db_run.external_id is not None, "external_id must exist for non-CREATED runs"

    engine = get_workflow_engine(db_run.workflow_revision.workflow.workflow_engine)
    canceled = await engine.cancel_workflow_run(db_run.external_id)
    if not canceled:
        logger.error(f"Failed to cancel workflow run in engine {workflow_run_id}")
        raise InternalError("Failed to cancel workflow run in engine")
    db_updated = await crud.update_workflow_run(
        db,
        run_id=workflow_run_id,
        workflow_run_update=schemas.WorkflowRunUpdate(
            external_id=db_run.external_id,
            lifecycle_status=schemas.WorkflowRunStatus.CANCELED,
        ),
    )
    await db.refresh(
        db_updated, attribute_names=["workflow_revision", "task_runs", "labels"]
    )
    return _workflow_run_to_schema(db_updated)


async def retry_workflow_run(
    db: AsyncSession, workflow_run_id: int
) -> schemas.WorkflowRun:
    """
    Retry a workflow run in the engine and persist the new lifecycle status.
    Returns the existing schema if the run is in a terminal state or in CREATED."""
    db_run = await crud.get_workflow_run(db, filters={"id": workflow_run_id})
    if not db_run:
        logger.error(f"No workflow runs found to retry {workflow_run_id}")
        raise NotFoundError("Workflow run not found")

    if db_run.lifecycle_status in [
        schemas.WorkflowRunStatus.COMPLETED,
        schemas.WorkflowRunStatus.ERROR,
        schemas.WorkflowRunStatus.CANCELED,
        schemas.WorkflowRunStatus.CREATED,
    ]:
        logger.info(
            f"Workflow run {workflow_run_id} is already in terminal state or in CREATED state:"
            f"{db_run.lifecycle_status.value} - returning existing state"
        )
        return _workflow_run_to_schema(db_run)

    assert db_run.external_id is not None, "external_id must exist for non-CREATED runs"

    engine = get_workflow_engine(db_run.workflow_revision.workflow.workflow_engine)
    new_run_status = await engine.retry_workflow_run(db_run.external_id)
    updated_run = await crud.update_workflow_run(
        db,
        run_id=workflow_run_id,
        workflow_run_update=schemas.WorkflowRunUpdate(
            lifecycle_status=new_run_status,
            external_id=db_run.external_id,
        ),
    )
    await db.refresh(
        updated_run, attribute_names=["workflow_revision", "task_runs", "labels"]
    )
    return _workflow_run_to_schema(updated_run)


async def get_workflow_run_task_runs(
    db: AsyncSession,
    workflow_run_id: int,
    task_title: Optional[str],
) -> List[schemas.TaskRun]:
    """
    List the task runs of a workflow run, optionally filtered by task title.
    For non-terminal runs, syncs task run state from the engine first so the returned list reflects the current state."""
    db_run = await crud.get_workflow_run(db, filters={"id": workflow_run_id})
    if not db_run:
        logger.error(f"No workflow run found for id {workflow_run_id}")
        raise NotFoundError("Workflow run not found")

    # get task runs from the engine adapter if the workflow run is not in a terminal state
    if db_run.lifecycle_status not in [
        schemas.WorkflowRunStatus.COMPLETED,
        schemas.WorkflowRunStatus.ERROR,
        schemas.WorkflowRunStatus.CANCELED,
        schemas.WorkflowRunStatus.CREATED,
    ]:
        assert (
            db_run.external_id is not None
        ), "external_id must exist for non-CREATED runs"
        engine = get_workflow_engine(db_run.workflow_revision.workflow.workflow_engine)
        task_run_updates = await engine.get_workflow_run_task_runs(db_run.external_id)
        logger.info(f"Got {len(task_run_updates)} task runs from the engine")

        for t in task_run_updates:
            await crud.create_or_update_task_run(db, t, workflow_run_id)

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
    """
    Get a single task run scoped to a workflow run.
    """
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
    """
    Fetch the engine logs for a specific task run. 
    Routes through the engine adapter resolved from the parent workflow's engine.
    """
    task_run = await crud.get_task_run(
        db, filters={"id": task_run_id, "workflow_run_id": workflow_run_id}
    )
    if not task_run:
        logger.error(f"Task run not found for {workflow_run_id=} and {task_run_id=}")
        raise NotFoundError("Task run not found")

    engine = get_workflow_engine(
        task_run.workflow_run.workflow_revision.workflow.workflow_engine
    )
    logs = await engine.get_task_run_logs(task_run.external_id)
    return logs


async def get_task_run_log_lines(
    db: AsyncSession, workflow_run_id: int, task_run_id: int
) -> list[schemas.LogLine]:
    """
    Fetches and parses the logs of a task run into structured LogLine objects.
    The raw log is retrieved from the engine adapter and parsed by the same adapter.
    Args:
        db (AsyncSession): Database session
        workflow_run_id (int): ID of the workflow run
        task_run_id (int): ID of the task run
    Returns:
        list[LogLine]: Parsed log lines with time, severity, message, and metadata
    Raises:
        NotFoundError: If the task run is not found
    """
    task_run = await crud.get_task_run(
        db, filters={"id": task_run_id, "workflow_run_id": workflow_run_id}
    )
    if not task_run:
        raise NotFoundError("Task run not found")

    engine = get_workflow_engine(task_run.workflow_run.workflow.workflow_engine)
    raw = await engine.get_task_run_logs(task_run.external_id)
    return engine.parse_task_run_logs(raw)


async def _submit_workflow_run_to_engine(
    db: AsyncSession,
    workflow_run: schemas.WorkflowRun,
    workflow_engine: WorkflowEngineAdapter,
    project_id: str,
) -> None:
    """Background task that submits a created workflow run to the engine and persists the engine-assigned `external_id` + initial lifecycle status."""
    wf_run_update = await workflow_engine.submit_workflow_run(
        workflow_run, project_id=project_id
    )
    logger.info(
        f"Submitted WorkflowRun {workflow_run.id} to engine, received update: {wf_run_update}"
    )
    if wf_run_update.external_id is None:
        logger.error(
            f"Workflow engine did not return an external_id for workflow run {workflow_run.id}"
        )
        raise InternalError("Workflow engine did not return an external_id")
    await crud.update_workflow_run(db, workflow_run.id, wf_run_update)


async def _sync_single_workflow_run(db: AsyncSession, run: models.WorkflowRun) -> None:
    """
    Pull the latest lifecycle status and task-run states for one run from the engine and persist them. 
    Skips runs in terminal/CREATED states.
    """
    if run.lifecycle_status in [
        schemas.WorkflowRunStatus.COMPLETED,
        schemas.WorkflowRunStatus.ERROR,
        schemas.WorkflowRunStatus.CANCELED,
        schemas.WorkflowRunStatus.CREATED,
    ]:
        logger.debug(f"Skipping sync for terminal or CREATED run {run.id}")
        return

    assert run.external_id is not None, "external_id must exist for non-CREATED runs"

    try:
        engine = get_workflow_engine(run.workflow_revision.workflow.workflow_engine)
        # update workflow run status
        status = await engine.get_workflow_run_status(run.external_id)
        if status != run.lifecycle_status:
            logger.info(f"Syncing Run {run.id}: {run.lifecycle_status} -> {status}")
            await crud.update_workflow_run(
                db=db,
                run_id=run.id,
                workflow_run_update=schemas.WorkflowRunUpdate(lifecycle_status=status),
            )

        # update task runs in the background
        task_run_updates = await engine.get_workflow_run_task_runs(run.external_id)
        for t in task_run_updates:
            # await here to ensure DB integrity during the sync job
            await crud.create_or_update_task_run(
                db=db,
                task_run_update=t,
                workflow_run_id=run.id,
            )
    except Exception as e:
        logger.error(f"Error syncing workflow run {run.id}: {e}")
        raise InternalError(f"Error syncing workflow run {run.id}: {e}")


async def sync_active_runs(db: AsyncSession):
    """
    Periodic sweep over all non-terminal workflow runs. 
    Pulls engine state for each and updates lifecycle/task-run rows.
    """
    logger.info("Starting periodic sync of active workflow runs...")
    active_runs = await crud.get_active_workflow_runs(db)
    if not active_runs:
        logger.debug("No active runs to sync.")
        return
    logger.info(f"Found {len(active_runs)} active runs. Syncing...")
    for run in active_runs:
        await _sync_single_workflow_run(db, run)
    logger.info("Periodic sync finished.")
