import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

from app import crud, models, schemas
from app.adapters import WorkflowEngineAdapter, get_workflow_engine
from app.api.v1.services.errors import InternalError, NotFoundError
from app.api.v1.services.utils import run_in_background_with_retries
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# Helpers


def _revision_to_schema(rev: models.WorkflowRevision) -> schemas.WorkflowRevision:
    return schemas.WorkflowRevision(
        id=rev.id,
        workflow_id=rev.workflow_id,
        workflow_title=rev.workflow.title,
        increment=rev.increment,
        definition=rev.definition,
        workflow_parameters=rev.workflow_parameters or [],
        labels=rev.labels or [],
        created_at=rev.created_at,
    )


def _workflow_to_schema(db_workflow: models.Workflow) -> schemas.Workflow:
    """Merge the latest revision's fields into the workflow series for the response."""
    current = crud.latest_revision(db_workflow)
    return schemas.Workflow(
        id=db_workflow.id,
        title=db_workflow.title,
        workflow_engine=db_workflow.workflow_engine,
        created_at=db_workflow.created_at,
        increment=current.increment,
        definition=current.definition,
        workflow_parameters=current.workflow_parameters or [],
        labels=current.labels or [],
    )


def _enforce_immutable_labels(
    current_labels,
    new_labels,
    *,
    detail_prefix: str = "",
) -> None:
    """
    Enforce the `kaapana.immutable.*` invariant across two label sets.

    Accepts any iterables of label-like objects with `.key` and `.value` (ORM `Label` rows or Pydantic `Label` schemas).
    Raises `HTTPException(422)` on violation.
    """
    current_pairs = [(l.key, l.value) for l in current_labels]
    new_pairs = [(l.key, l.value) for l in new_labels]
    try:
        crud.check_immutable_labels(current_pairs, new_pairs)
    except crud.ImmutableLabelViolation as e:
        detail = f"{detail_prefix}{e}" if detail_prefix else str(e)
        raise HTTPException(status_code=422, detail=detail)


# Workflow service operations


async def get_workflows(
    db: AsyncSession,
    skip: int,
    limit: int,
    order_by: Optional[str],
    order: Optional[str],
    id: Optional[uuid.UUID],
    title: Optional[str],
) -> List[schemas.Workflow]:
    """
    List active workflows, with optional filtering by `id` or `title`.
    """
    filters: Dict[str, Any] = {}
    if id is not None:
        filters["id"] = id
    if title is not None:
        filters["title"] = title
    db_workflows = await crud.get_workflows(
        db, skip=skip, limit=limit, order_by=order_by, order=order, filters=filters
    )
    if not db_workflows:
        logger.warning(f"No workflows found with filters: {filters}")
        return []
    return [_workflow_to_schema(w) for w in db_workflows]


async def create_workflow(
    db: AsyncSession, workflow: schemas.WorkflowCreate
) -> schemas.Workflow:
    """
    Create a workflow. 409 when the title already exists in another active workflow.
    """
    existing = await crud.get_workflow(db, filters={"title": workflow.title})
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"Workflow with title '{workflow.title}' already exists.",
                "existing_workflow": {"id": str(existing.id)},
            },
        )

    try:
        db_workflow = await crud.create_workflow(db, workflow=workflow)
    except IntegrityError as e:
        # another POST inserted the same title between the pre-flight read and the insert attempt
        await db.rollback()
        logger.warning(f"Workflow create rejected by DB constraint: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"A workflow with title '{workflow.title}' already exists",
        )
    if not db_workflow:
        logger.error(f"Failed to create workflow: {workflow}")
        raise InternalError("Failed to create workflow")

    current = crud.latest_revision(db_workflow)
    logger.info(f"Created workflow: {db_workflow.title} inc{current.increment}")

    schema_workflow = _workflow_to_schema(db_workflow)
    schema_revision = _revision_to_schema(current)

    engine = get_workflow_engine(db_workflow.workflow_engine)
    await engine.submit_workflow_revision(revision=schema_revision)

    # parse workflow tasks in the background with retries
    asyncio.create_task(
        run_in_background_with_retries(
            _parse_revision_tasks,
            db=db,
            revision_id=current.id,
            engine=engine,
            max_retries=5,
            delay_seconds=10,
        )
    )
    # return the created workflow immediately before tasks are parsed
    return schema_workflow


async def get_workflow_by_id(
    db: AsyncSession,
    workflow_id: uuid.UUID,
) -> schemas.Workflow:
    """
    Get a single workflow by UUID.
    """
    db_workflow = await crud.get_workflow(db, filters={"id": workflow_id})
    if not db_workflow:
        logger.error(f"Workflow with id {workflow_id} not found")
        raise NotFoundError("Workflow not found")
    return _workflow_to_schema(db_workflow)


async def update_workflow(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    update: schemas.WorkflowUpdate,
) -> schemas.Workflow:
    """
    Apply a partial update to a workflow.
    A change to any versioned field (definition, parameters, labels) appends a new revision and bumps the increment.
    Change in title updates the workflow row in place.
    If the definition changed, the new revision is submitted to the engine and its tasks are parsed in the background.
    """
    db_workflow = await crud.get_workflow(db, filters={"id": workflow_id})
    if not db_workflow:
        logger.error(f"Workflow with id {workflow_id} not found")
        raise NotFoundError("Workflow not found")

    if update.title is not None and update.title != db_workflow.title:
        conflict = await crud.get_workflow(db, filters={"title": update.title})
        if conflict is not None and conflict.id != db_workflow.id:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot rename workflow: a workflow with title '{update.title}' already exists",
            )

    # If the PATCH touches labels, enforce immutability of any kaapana.immutable.* label that's already on the latest revision
    if update.labels is not None:
        current_rev = crud.latest_revision(db_workflow)
        _enforce_immutable_labels(current_rev.labels, update.labels)

    try:
        db_workflow = await crud.update_workflow(db, db_workflow, update)
    except IntegrityError as e:
        await db.rollback()
        logger.warning(f"Workflow update rejected by DB constraint: {e}")
        raise HTTPException(
            status_code=409,
            detail="Workflow update violates a database constraint",
        )
    current = crud.latest_revision(db_workflow)

    # Submit the new revision to the engine whenever a versioned field changed (definition / parameters / labels)
    # Any of them appends a new revision, and the Airflow dag_id is based on (title, increment), so the matching DAG file must be (re-)registered for that new increment
    versioned_change = (
        update.definition is not None
        or update.workflow_parameters is not None
        or update.labels is not None
    )
    if versioned_change:
        engine = get_workflow_engine(db_workflow.workflow_engine)
        await engine.submit_workflow_revision(revision=_revision_to_schema(current))
        asyncio.create_task(
            run_in_background_with_retries(
                _parse_revision_tasks,
                db=db,
                revision_id=current.id,
                engine=engine,
                max_retries=5,
                delay_seconds=10,
            )
        )

    return _workflow_to_schema(db_workflow)


async def restore_workflow_revision(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    target_increment: int,
) -> schemas.Workflow:
    """
    Restore a workflow to a previous revision's content by appending a new revision that copies the target revision's snapshot.
    The workflow's history is preserved (append-only). The new revision is submitted to the engine and its tasks are parsed in the background.
    """
    db_workflow = await crud.get_workflow(db, filters={"id": workflow_id})
    if not db_workflow:
        raise NotFoundError("Workflow not found")

    # Restore must satisfy the same immutability rule as update
    target = next(
        (r for r in db_workflow.revisions if r.increment == target_increment),
        None,
    )
    current_rev = crud.latest_revision(db_workflow)
    if target is not None and current_rev is not None:
        _enforce_immutable_labels(
            current_rev.labels,
            target.labels,
            detail_prefix=(
                f"Cannot restore workflow {workflow_id} to increment "
                f"{target_increment}: "
            ),
        )

    try:
        db_workflow = await crud.restore_workflow_revision(
            db, db_workflow, target_increment
        )
    except ValueError as e:
        raise NotFoundError(str(e))

    current = crud.latest_revision(db_workflow)
    engine = get_workflow_engine(db_workflow.workflow_engine)
    await engine.submit_workflow_revision(revision=_revision_to_schema(current))
    asyncio.create_task(
        run_in_background_with_retries(
            _parse_revision_tasks,
            db=db,
            revision_id=current.id,
            engine=engine,
            max_retries=5,
            delay_seconds=10,
        )
    )

    return _workflow_to_schema(db_workflow)


async def delete_workflow(db: AsyncSession, workflow_id: uuid.UUID):
    """
    Soft-delete a workflow: sets `removed=True` on the workflow row.
    """
    db_workflow = await crud.get_workflow(db, filters={"id": workflow_id})
    success = await crud.delete_workflow(db, db_workflow) if db_workflow else False
    # workflow is already filtered by removed=False, so removed ones are not returned
    if not success:
        logger.error(f"Failed to delete workflow with id {workflow_id}")
        raise NotFoundError("Workflow not found")


# Revisions


async def get_workflow_revisions(
    db: AsyncSession, workflow_id: uuid.UUID
) -> List[schemas.WorkflowRevision]:
    """List every revision of a workflow in increment order."""
    db_workflow = await crud.get_workflow(db, filters={"id": workflow_id})
    if not db_workflow:
        raise NotFoundError("Workflow not found")
    return [_revision_to_schema(r) for r in db_workflow.revisions]


async def get_workflow_revision(
    db: AsyncSession, workflow_id: uuid.UUID, increment: int
) -> schemas.WorkflowRevision:
    """Get a single revision of a workflow."""
    rev = await crud.get_workflow_revision(db, workflow_id, increment)
    if rev is None or rev.workflow.removed:
        raise NotFoundError("Workflow revision not found")
    return _revision_to_schema(rev)


# Tasks


async def get_workflow_tasks(
    db: AsyncSession, workflow_id: uuid.UUID, increment: Optional[int] = None
) -> List[schemas.Task]:
    """
    List tasks for a workflow's specific revision (latest if increment=None).
    If tasks haven't been parsed yet, parses them just-in-time and returns the result.
    """
    db_workflow = await crud.get_workflow(db, filters={"id": workflow_id})
    if not db_workflow:
        raise NotFoundError("Workflow not found")

    if increment is None:
        target_revision = crud.latest_revision(db_workflow)
    else:
        target_revision = next(
            (r for r in db_workflow.revisions if r.increment == increment), None
        )
    if target_revision is None:
        raise NotFoundError("Workflow revision not found")

    tasks = await crud.get_tasks(
        db, filters={"workflow_revision_id": target_revision.id}
    )
    if not tasks:
        # Tasks may not have been parsed yet, parse just-in-time and re-query
        engine = get_workflow_engine(db_workflow.workflow_engine)
        await _parse_revision_tasks(
            db=db, revision_id=target_revision.id, engine=engine
        )
        tasks = await crud.get_tasks(
            db, filters={"workflow_revision_id": target_revision.id}
        )

    res = []
    for t in tasks:
        task_data = jsonable_encoder(t)
        task_data["downstream_task_ids"] = [
            dt.downstream_task_id for dt in t.downstream_tasks
        ]
        res.append(schemas.Task.model_validate(task_data))
    return res


async def get_task(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    task_title: str,
    increment: Optional[int] = None,
) -> schemas.Task:
    """Get a single task by title from a workflow's revision (or latest)."""
    db_workflow = await crud.get_workflow(db, filters={"id": workflow_id})
    if not db_workflow:
        raise NotFoundError("Workflow not found")

    if increment is None:
        target_revision = crud.latest_revision(db_workflow)
    else:
        target_revision = next(
            (r for r in db_workflow.revisions if r.increment == increment), None
        )
    if target_revision is None:
        raise NotFoundError("Workflow revision not found")

    task = await crud.get_task(
        db,
        filters={
            "title": task_title,
            "workflow_revision_id": target_revision.id,
        },
    )
    if not task:
        logger.error(
            f"Task {task_title} for workflow {workflow_id} inc{target_revision.increment} not found"
        )
        raise NotFoundError("Task not found")

    task_data = jsonable_encoder(task)
    task_data["downstream_task_ids"] = [
        dt.downstream_task_id for dt in task.downstream_tasks
    ]
    return schemas.Task(**task_data)


# Internal: engine-side task parsing for a revision


async def _parse_revision_tasks(
    db: AsyncSession,
    revision_id: uuid.UUID,
    engine: WorkflowEngineAdapter,
):
    """Fetch tasks from the engine for a specific revision and persist them.

    Reloads the revision from `db` (a fresh session opened by
    run_in_background_with_retries) so we never read attributes off an ORM
    instance bound to the request-scoped session that has already closed.
    """
    db_revision = await crud.get_workflow_revision_by_id(db, revision_id)
    if db_revision is None:
        logger.error(f"Revision {revision_id} disappeared before tasks could be parsed")
        return
    schema_revision = _revision_to_schema(db_revision)

    tasks: List[schemas.TaskCreate] = await engine.get_workflow_tasks(
        revision=schema_revision
    )

    db_tasks: Dict[str, models.Task] = {}
    for task_create in tasks:
        t = await crud.create_task(
            db=db, task=task_create, workflow_revision_id=db_revision.id
        )
        db_tasks[t.title] = t
        logger.info(f"Created task {t.title} for revision {db_revision.id}")

    for task_from_engine in tasks:
        db_task = db_tasks.get(task_from_engine.title)
        if not db_task:
            continue
        for ds_title in task_from_engine.downstream_task_titles:
            ds_task = db_tasks.get(ds_title)
            if not ds_task:
                logger.error(
                    f"Failed to find downstream task {ds_title} to link to {db_task.title}."
                )
                continue
            await crud.add_downstream_task(
                db, task_id=db_task.id, downstream_task_id=ds_task.id
            )

    await db.commit()
    logger.info(
        f"Successfully parsed tasks for workflow {db_revision.workflow_id} inc{db_revision.increment}."
    )
