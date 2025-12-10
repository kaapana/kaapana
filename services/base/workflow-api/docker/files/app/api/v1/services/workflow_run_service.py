import asyncio
import logging
from typing import Any, List, Optional

from app import crud, models, schemas
from app.adapters import WorkflowEngineAdapter, get_workflow_engine
from app.api.v1.services.errors import InternalError, NotFoundError
from app.api.v1.services.utils import run_in_background_with_retries
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_workflow_runs(
    db: AsyncSession,
    workflow_title: Optional[str],
    workflow_version: Optional[int],
    lifecycle_status: Optional[str] = None,
) -> List[schemas.WorkflowRun]:
    """
    Gets workflow runs from workflow DB, optionally filtered by workflow title and version.

    Args:
        db (AsyncSession): Database session
        workflow_title (Optional[str]): Title of the workflow to filter by
        workflow_version (Optional[int]): Version of the workflow to filter by
    Returns:
        List[WorkflowRun]: List of WorkflowRun objects
    """

    filters = {}
    if workflow_title:
        filters["workflow.title"] = workflow_title
    if workflow_version:
        filters["workflow.version"] = str(workflow_version)
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
        # if a run is in a terminal state, no need to sync with engine, as well as if it was just created and not yet recognized by engine
        if db_run.lifecycle_status in [
            schemas.WorkflowRunStatus.COMPLETED,
            schemas.WorkflowRunStatus.ERROR,
            schemas.WorkflowRunStatus.CANCELED,
            schemas.WorkflowRunStatus.CREATED,
        ]:
            res.append(db_run)
            continue

        # Now we know run.external_id must exist
        assert (
            db_run.external_id is not None
        ), "external_id must exist for non-CREATED runs"

        # get status from the engine
        engine = get_workflow_engine(db_run.workflow.workflow_engine)
        status = await engine.get_workflow_run_status(db_run.external_id)
        if status != db_run.lifecycle_status:
            await crud.update_workflow_run(
                db=db,
                run_id=db_run.id,
                workflow_run_update=schemas.WorkflowRunUpdate(lifecycle_status=status),
            )

        # update all task runs of workflow run in the background
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
    return [schemas.WorkflowRun.model_validate(r) for r in res]


async def create_workflow_run(
    db: AsyncSession,
    workflow_run: schemas.WorkflowRunCreate,
    project_id: str,
) -> schemas.WorkflowRun:
    """
    Creates a new workflow run in the database and submits it to the workflow engine as a background task.

    Args:
        db (AsyncSession): Database session
        workflow_run (WorkflowRunCreate): Workflow run data to create
    Returns:
        WorkflowRun: The created WorkflowRun object
    Side Effects:
        - Spawns a background task with func run_in_background_with_retries() to submit the workflow run to the workflow engine

    """
    logger.debug(f"Creating workflow run for {workflow_run=}")

    db_workflow = await crud.get_workflow(
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
        run_in_background_with_retries(
            _submit_workflow_run_to_engine,
            db=db,
            workflow_run=schemas.WorkflowRun.model_validate(db_workflow_run),
            workflow_engine=engine,
            project_id=project_id,
        )
    )

    return schemas.WorkflowRun.model_validate(db_workflow_run)


async def get_workflow_run_by_id(
    db: AsyncSession, workflow_run_id: int
) -> schemas.WorkflowRun:
    """
    Gets a workflow run by its ID, syncing its status with the workflow engine if necessary.
    Args:
        db (AsyncSession): Database session
        workflow_run_id (int): ID of the workflow run to retrieve
    Returns:
        WorkflowRun: The WorkflowRun object with updated status
    Raises:
        NotFoundError: If the workflow run is not found
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
        return schemas.WorkflowRun.model_validate(db_run)

    assert db_run.external_id is not None, "external_id must exist for non-CREATED runs"

    engine = get_workflow_engine(db_run.workflow.workflow_engine)
    status = await engine.get_workflow_run_status(db_run.external_id)
    if status != db_run.lifecycle_status:
        db_run = await crud.update_workflow_run(
            db=db,
            run_id=workflow_run_id,
            workflow_run_update=schemas.WorkflowRunUpdate(lifecycle_status=status),
        )
    return schemas.WorkflowRun.model_validate(db_run)


async def cancel_workflow_run(
    db: AsyncSession, workflow_run_id: int
) -> schemas.WorkflowRun:
    """
    Updates the status of a workflow run to canceled in workflow db and cancels the run in the workflow engine.

    For workflows in terminal states (COMPLETED, ERROR, CANCELED), this is a no-op that returns
    the existing state without error - preserving idempotency and state immutability.

    Args:
        db (AsyncSession): Database session
        workflow_run_id (int): ID of the workflow run to cancel
    Returns:
        WorkflowRun: The workflow run object (updated to CANCELED if it was active, unchanged if terminal)
    Raises:
        NotFoundError: If the workflow run is not found
        InternalError: If the cancellation in the workflow engine fails for non-terminal runs
    """
    db_run = await crud.get_workflow_run(db, filters={"id": workflow_run_id})
    if not db_run:
        logger.error(f"No workflow runs found to cancel {workflow_run_id}")
        raise NotFoundError("Workflow run not found")

    # Terminal states are immutable - return existing state without error (idempotent no-op)
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
        return schemas.WorkflowRun.model_validate(db_run)

    assert db_run.external_id is not None, "external_id must exist for non-CREATED runs"

    engine = get_workflow_engine(db_run.workflow.workflow_engine)
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
    return schemas.WorkflowRun.model_validate(db_updated)


async def retry_workflow_run(
    db: AsyncSession, workflow_run_id: int
) -> schemas.WorkflowRun:
    """
    Retries a workflow run in the workflow engine, retrieves and updates its status in the workflow db.
    Args:
        db (AsyncSession): Database session
        workflow_run_id (int): ID of the workflow run to retry
    Returns:
        WorkflowRun: The updated WorkflowRun object
    Raises:
        NotFoundError: If the workflow run is not found
    """
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
        return schemas.WorkflowRun.model_validate(db_run)

    assert db_run.external_id is not None, "external_id must exist for non-CREATED runs"

    engine = get_workflow_engine(db_run.workflow.workflow_engine)
    new_run_status = await engine.retry_workflow_run(db_run.external_id)

    updated_run = await crud.update_workflow_run(
        db,
        run_id=workflow_run_id,
        workflow_run_update=schemas.WorkflowRunUpdate(
            lifecycle_status=new_run_status,
            external_id=db_run.external_id,
        ),
    )
    return schemas.WorkflowRun.model_validate(updated_run)


async def get_workflow_run_task_runs(
    db: AsyncSession,
    workflow_run_id: int,
    task_title: Optional[str],  # Only include task-runs for this task title
) -> List[schemas.TaskRun]:
    """
    Gets the task runs of a workflow run, syncing with the workflow engine if necessary.
    Args:
        db (AsyncSession): Database session
        workflow_run_id (int): ID of the workflow run
        task_title (Optional[str]): Title of the task to filter by
    Returns:
        List[TaskRun]: List of TaskRun objects
    Raises:
        NotFoundError: If the workflow run or task runs are not found

    """
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
        engine = get_workflow_engine(db_run.workflow.workflow_engine)
        task_run_updates = await engine.get_workflow_run_task_runs(db_run.external_id)
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
    """
    Gets a specific task run of a workflow run.
    Args:
        db (AsyncSession): Database session
        workflow_run_id (int): ID of the workflow run
        task_run_id (int): ID of the task run
    Returns:
        TaskRun: The TaskRun object
    Raises:
        NotFoundError: If the task run is not found
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
    Gets the logs of a specific task run of a workflow run.
    Args:
        db (AsyncSession): Database session
        workflow_run_id (int): ID of the workflow run
        task_run_id (int): ID of the task run
    Returns:
        str: The logs of the task run
    Raises:
        NotFoundError: If the task run is not found
    """
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


async def _submit_workflow_run_to_engine(
    db: AsyncSession,
    workflow_run: schemas.WorkflowRun,
    workflow_engine: WorkflowEngineAdapter,
    project_id: str,
) -> None:
    """
    Submits a workflow run to the workflow engine and updates the database with the returned external ID and status values.
    Args:
        db (AsyncSession): Database session
        workflow_run (WorkflowRun): The workflow run to submit
        workflow_engine (WorkflowEngineAdapter): The workflow engine adapter to submit
    Returns:
        None
    Raises:
        InternalError: If the workflow engine does not return an external ID
    """
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
    Syncs a single workflow run and its tasks with the engine.
    Args:
        db (AsyncSession): Database session
        run (WorkflowRun): The workflow run to sync
    Returns:
        None
    Raises:
        InternalError: If syncing fails
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
        engine = get_workflow_engine(run.workflow.workflow_engine)

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
    Fetches all active workflow runs and syncs them with the engine.
    Args:
        db (AsyncSession): Database session
    Returns:
        None
    Raises:
        InternalError: If syncing fails (via _sync_single_workflow_run)
    """
    # TODO: currently does not account for the cases where both syncing and cancellation fails (i.e. zombie runs)

    logger.info("Starting periodic sync of active workflow runs...")

    # fetch active runs (not in completed,failed,canceled)
    active_runs = await crud.get_active_workflow_runs(db)

    if not active_runs:
        logger.debug("No active runs to sync.")
        return

    logger.info(f"Found {len(active_runs)} active runs. Syncing...")

    for run in active_runs:
        await _sync_single_workflow_run(db, run)

    logger.info("Periodic sync finished.")
