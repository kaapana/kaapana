import hashlib
import json
import logging
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

from fastapi.encoders import jsonable_encoder
from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models, schemas

logger = logging.getLogger(__name__)


# Helpers


def create_query(
    model: Type[Any],
    filters: Optional[Dict[str, Any]] = None,
    eager_load: Optional[List[str]] = None,
    order_by: Optional[Any] = None,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
) -> Select[Any]:
    query: Select[Any] = select(model)

    # Apply eager loading. A dotted entry (e.g. "workflow_run.workflow_revision.workflow") is loaded as a nested selectinload chain.
    if eager_load:
        for relation in eager_load:
            parts = relation.split(".")
            current_model = model
            loader = None
            for part in parts:
                attr = getattr(current_model, part)
                loader = loader.selectinload(attr) if loader else selectinload(attr)
                current_model = attr.property.mapper.class_
            query = query.options(loader)

    # Apply filters
    if filters:
        for attr, value in filters.items():
            if "." in attr:  # related field filtering
                rel_name, col_name = attr.split(".", 1)
                rel = getattr(model, rel_name)
                col = getattr(rel.property.mapper.class_, col_name)
                query = query.join(rel).filter(col == value)
            else:  # direct field filtering
                query = query.filter(getattr(model, attr) == value)

    # Apply ordering
    if order_by is not None:
        query = query.order_by(order_by)

    # Apply pagination
    if skip is not None:
        query = query.offset(skip)
    if limit is not None:
        query = query.limit(limit)

    logger.debug(f"Constructed GET query: {query}")

    return query


def latest_revision(db_workflow: models.Workflow) -> Optional[models.WorkflowRevision]:
    """
    Return the WorkflowRevision with the highest `increment` for the given workflow.
    """
    if not db_workflow.revisions:
        return None
    return max(db_workflow.revisions, key=lambda r: r.increment)


# Labels


async def _get_or_create_labels(
    db: AsyncSession, labels: List[schemas.Label]
) -> List[models.Label]:
    """
    Get or create `Label` rows for a list of (key, value) pairs.
    Return the persisted ORM objects suitable for attaching to a relationship.
    """
    db_labels: List[models.Label] = []
    for label in labels or []:
        # add new labels if they don't already exist
        insert_stmt = (
            insert(models.Label)
            .values(key=label.key, value=label.value)
            .on_conflict_do_nothing(index_elements=["key", "value"])
        )
        await db.execute(insert_stmt)
        # fetch the label
        stmt = select(models.Label).where(
            models.Label.key == label.key, models.Label.value == label.value
        )
        result = await db.execute(stmt)
        db_label = result.scalars().first()
        if db_label is None:
            db_label = models.Label(key=label.key, value=label.value)
        db_labels.append(db_label)
    return db_labels


# Any label whose key starts with this prefix is treated as immutable across revisions
IMMUTABLE_LABEL_PREFIX = "kaapana.immutable."


class ImmutableLabelViolation(Exception):
    """Raised when a label update would change or remove an immutable label."""


def check_immutable_labels(
    current: List[Tuple[str, str]],
    new: List[Tuple[str, str]],
) -> None:
    """Verify that all immutable labels are present in `current` are preserved in `new` with the same value.

    Args:
        current: (key, value) pairs from the current state.
        new: (key, value) pairs proposed for the next state.

    Raises:
        ImmutableLabelViolation: if any `kaapana.immutable.*` label in `current` is missing or has a different value in `new`.
    """
    new_by_key = dict(new)
    for key, value in current:
        if not key.startswith(IMMUTABLE_LABEL_PREFIX):
            continue
        if key not in new_by_key:
            raise ImmutableLabelViolation(
                f"Cannot remove immutable label '{key}'. Labels with prefix '{IMMUTABLE_LABEL_PREFIX}' are immutable."
            )
        if new_by_key[key] != value:
            raise ImmutableLabelViolation(
                f"Cannot change value of immutable label '{key}' from '{value}' to '{new_by_key[key]}'."
            )


def compute_spec_hash(
    definition: str,
    workflow_parameters: Optional[Iterable[Any]],
    labels: Optional[Iterable[Any]],
) -> str:
    """
    SHA-256 over (labels, workflow_parameters, definition).

    Accepts any iterables of label/parameter-like objects (ORM rows, Pydantic models, dicts, or (key, value) tuples for labels).
    """
    label_pairs: List[Tuple[str, str]] = []
    for label in labels or []:
        if hasattr(label, "key") and hasattr(label, "value"):
            label_pairs.append((label.key, label.value))
        elif isinstance(label, dict):
            label_pairs.append((label["key"], label["value"]))
        else:
            label_pairs.append((label[0], label[1]))
    label_pairs.sort()

    param_dicts: List[dict] = []
    for param in workflow_parameters or []:
        if hasattr(param, "model_dump"):
            param_dicts.append(param.model_dump())
        elif isinstance(param, dict):
            param_dicts.append(param)
        else:
            param_dicts.append(jsonable_encoder(param))
    param_dicts.sort(
        key=lambda d: (d.get("task_title", ""), d.get("env_variable_name", ""))
    )

    canonical = json.dumps(
        {
            "definition": definition,
            "workflow_parameters": param_dicts,
            "labels": label_pairs,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Workflows


async def get_workflows(
    db: AsyncSession,
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    order: Optional[str] = "desc",
    skip: int = 0,
    limit: int = 100,
) -> List[models.Workflow]:
    order_by_exp = models.Workflow.created_at.desc()
    if order_by:
        order_col = getattr(models.Workflow, order_by, None)
        if order_col is not None:
            order_by_exp = order_col.asc() if order == "asc" else order_col.desc()

    filters = filters or {}
    filters["removed"] = False
    query = create_query(
        model=models.Workflow,
        filters=filters,
        eager_load=["revisions"],
        order_by=order_by_exp,
        skip=skip,
        limit=limit,
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_workflow(
    db: AsyncSession,
    filters: Optional[Dict[str, Any]] = None,
) -> Optional[models.Workflow]:
    filters = filters or {}
    filters["removed"] = False
    query = create_query(
        model=models.Workflow,
        filters=filters,
        eager_load=["revisions"],
    )
    result = await db.execute(query)
    return result.scalars().first()


async def create_workflow(
    db: AsyncSession, workflow: schemas.WorkflowCreate
) -> models.Workflow:
    """Create a new workflow with its first revision (increment=1)"""
    params_json = jsonable_encoder(workflow.workflow_parameters or [])
    db_labels = await _get_or_create_labels(db, workflow.labels or [])
    spec_hash = compute_spec_hash(
        definition=workflow.definition,
        workflow_parameters=workflow.workflow_parameters,
        labels=workflow.labels,
    )

    db_workflow = models.Workflow(
        title=workflow.title,
        workflow_engine=workflow.workflow_engine,
    )
    db_workflow.revisions = [
        models.WorkflowRevision(
            increment=1,
            definition=workflow.definition,
            workflow_parameters=params_json,
            labels=db_labels,
            spec_hash=spec_hash,
        )
    ]
    db.add(db_workflow)
    await db.commit()
    await db.refresh(db_workflow)
    return db_workflow


async def update_workflow(
    db: AsyncSession,
    db_workflow: models.Workflow,
    update: schemas.WorkflowUpdate,
) -> models.Workflow:
    """
    Apply a workflow update.

    A change to any versioned field (definition, parameters, labels) appends a new revision.
    A title-only change updates the workflow row in place.
    """
    current = latest_revision(db_workflow)
    if current is None:
        raise ValueError(f"Workflow {db_workflow.id} has no revisions to update")

    versioned_change = (
        update.definition is not None
        or update.workflow_parameters is not None
        or update.labels is not None
    )

    if versioned_change:
        new_definition = (
            update.definition if update.definition is not None else current.definition
        )
        new_params = (
            jsonable_encoder(update.workflow_parameters)
            if update.workflow_parameters is not None
            else current.workflow_parameters
        )
        new_labels = (
            await _get_or_create_labels(db, update.labels)
            if update.labels is not None
            else list(current.labels)
        )

        new_spec_hash = compute_spec_hash(
            definition=new_definition,
            workflow_parameters=new_params,
            labels=new_labels,
        )
        next_increment = current.increment + 1
        new_rev = models.WorkflowRevision(
            workflow_id=db_workflow.id,
            increment=next_increment,
            definition=new_definition,
            workflow_parameters=new_params,
            labels=new_labels,
            spec_hash=new_spec_hash,
        )
        db.add(new_rev)

    # Update title in place
    if update.title is not None and update.title != db_workflow.title:
        db_workflow.title = update.title

    await db.commit()
    # Refresh when a new revision was appended
    if versioned_change:
        await db.refresh(db_workflow)
    return db_workflow


async def delete_workflow(db: AsyncSession, db_workflow: models.Workflow) -> bool:
    if not db_workflow:
        return False
    db_workflow.removed = True  # soft delete
    await db.commit()
    return True


# Workflow Revisions


async def restore_workflow_revision(
    db: AsyncSession, db_workflow: models.Workflow, target_increment: int
) -> models.Workflow:
    """Append a new revision whose snapshot copies the requested earlier increment."""
    target = next(
        (r for r in db_workflow.revisions if r.increment == target_increment), None
    )
    if target is None:
        raise ValueError(
            f"Workflow {db_workflow.id} has no revision with increment={target_increment}"
        )
    current = latest_revision(db_workflow)
    assert current is not None
    next_increment = current.increment + 1
    new_rev = models.WorkflowRevision(
        workflow_id=db_workflow.id,
        increment=next_increment,
        definition=target.definition,
        workflow_parameters=target.workflow_parameters,
        labels=list(target.labels),
        spec_hash=target.spec_hash,
    )
    db.add(new_rev)
    await db.commit()
    await db.refresh(db_workflow)
    return db_workflow


async def get_workflow_revision(
    db: AsyncSession, workflow_id: uuid.UUID, increment: int
) -> Optional[models.WorkflowRevision]:
    query = (
        select(models.WorkflowRevision)
        .where(
            models.WorkflowRevision.workflow_id == workflow_id,
            models.WorkflowRevision.increment == increment,
        )
        .options(selectinload(models.WorkflowRevision.workflow))
    )
    result = await db.execute(query)
    return result.scalars().first()


async def get_workflow_revision_by_id(
    db: AsyncSession, revision_id: uuid.UUID
) -> Optional[models.WorkflowRevision]:
    query = (
        select(models.WorkflowRevision)
        .where(models.WorkflowRevision.id == revision_id)
        .options(selectinload(models.WorkflowRevision.workflow))
    )
    result = await db.execute(query)
    return result.scalars().first()


# WorkflowRun


async def get_active_workflow_runs(
    db: AsyncSession,
) -> List[models.WorkflowRun]:
    not_syncable_states = [
        schemas.WorkflowRunStatus.COMPLETED,
        schemas.WorkflowRunStatus.ERROR,
        schemas.WorkflowRunStatus.CANCELED,
        schemas.WorkflowRunStatus.CREATED,
    ]
    query = (
        select(models.WorkflowRun)
        .where(models.WorkflowRun.lifecycle_status.not_in(not_syncable_states))
        .options(selectinload(models.WorkflowRun.workflow_revision))
        .order_by(models.WorkflowRun.id.desc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_workflow_runs(
    db: AsyncSession,
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[Any] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.WorkflowRun]:
    query: Select[Any] = create_query(
        model=models.WorkflowRun,
        filters=filters,
        eager_load=["task_runs", "workflow_revision"],
        order_by=order_by or models.WorkflowRun.id.desc(),
        skip=skip,
        limit=limit,
    )

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_workflow_run(
    db: AsyncSession,
    filters: Optional[Dict[str, Any]] = None,
) -> Optional[models.WorkflowRun]:
    query: Select[Any] = create_query(
        model=models.WorkflowRun,
        filters=filters or {},
        eager_load=["task_runs", "workflow_revision"],
    )

    result = await db.execute(query)
    return result.scalars().first()


async def create_workflow_run(
    db: AsyncSession,
    workflow_run: schemas.WorkflowRunCreate,
    workflow_revision_id: uuid.UUID,
) -> models.WorkflowRun:
    db_labels: List[models.Label] = []
    for label in getattr(workflow_run, "labels", []) or []:
        insert_stmt = (
            insert(models.Label)
            .values(key=label.key, value=label.value)
            .on_conflict_do_nothing(index_elements=["key", "value"])
        )
        await db.execute(insert_stmt)

        stmt = select(models.Label).where(
            models.Label.key == label.key, models.Label.value == label.value
        )
        result = await db.execute(stmt)
        db_label = result.scalars().first()
        if not db_label:
            db_label = models.Label(key=label.key, value=label.value)
        db_labels.append(db_label)

    db_workflow_run = models.WorkflowRun(
        workflow_revision_id=workflow_revision_id,
        workflow_parameters=jsonable_encoder(workflow_run.workflow_parameters),
        labels=db_labels,
    )

    db.add(db_workflow_run)
    await db.commit()
    await db.refresh(db_workflow_run)

    return db_workflow_run


async def update_workflow_run(
    db: AsyncSession, run_id: int, workflow_run_update: schemas.WorkflowRunUpdate
) -> models.WorkflowRun:
    result = await db.execute(
        select(models.WorkflowRun).filter(models.WorkflowRun.id == run_id)
    )
    db_workflow_run = result.scalars().first()
    if not db_workflow_run:
        logger.error(f"Failed to update WorkflowRun {run_id=}")
        raise ValueError(f"Failed to update WorkflowRun: {run_id}")

    update_data = workflow_run_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_workflow_run, key, value)
    await db.commit()
    await db.refresh(db_workflow_run)

    return db_workflow_run


# Task


async def get_tasks(
    db: AsyncSession,
    order_by: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    order: Optional[str] = "desc",
    skip: int = 0,
    limit: int = 100,
) -> List[models.Task]:
    logger.info(
        f"Getting tasks with filters: {filters}, order_by: {order_by}, order: {order}, skip: {skip}, limit: {limit}"
    )
    # construct order_by expression
    order_by_exp = models.Task.id.desc()
    if order_by:
        order_col = getattr(models.Task, order_by, None)
        if order_col is not None:
            order_by_exp = order_col.asc() if order == "asc" else order_col.desc()

    query = create_query(
        model=models.Task,
        filters=filters or {},
        order_by=order_by_exp,
        eager_load=["downstream_tasks"],
        skip=skip,
        limit=limit,
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_task(
    db: AsyncSession,
    filters: Optional[Dict[str, Any]] = None,
) -> models.Task | None:
    query = create_query(
        model=models.Task,
        filters=filters or {},
        eager_load=["downstream_tasks"],
    )
    result = await db.execute(query)
    return result.scalars().first()


async def create_task(
    db: AsyncSession, task: schemas.TaskCreate, workflow_revision_id: uuid.UUID
) -> models.Task:
    logger.info(
        f"Creating task {task.title} for workflow_revision_id {workflow_revision_id}"
    )

    db_task = models.Task(
        workflow_revision_id=workflow_revision_id,
        title=task.title,
        display_name=task.display_name,
        type=task.type,
    )

    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)

    return db_task


async def add_downstream_task(
    db: AsyncSession, task_id: int, downstream_task_id: int
) -> models.DownstreamTask:
    stmt = select(models.DownstreamTask).where(
        models.DownstreamTask.task_id == task_id,
        models.DownstreamTask.downstream_task_id == downstream_task_id,
    )
    result = await db.execute(stmt)
    db_ds_task = result.scalars().first()
    if not db_ds_task:
        db_ds_task = models.DownstreamTask(
            task_id=task_id,
            downstream_task_id=downstream_task_id,
        )
        db.add(db_ds_task)
        await db.commit()
        await db.refresh(db_ds_task)
    return db_ds_task


# TaskRun


async def get_task_runs(
    db: AsyncSession,
    filters: Optional[Dict[str, Any]] = None,
) -> List[models.TaskRun]:
    query: Select[Any] = create_query(
        model=models.TaskRun,
        filters=filters or {},
        eager_load=["task", "workflow_run"],
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_task_run(
    db: AsyncSession,
    filters: Optional[Dict[str, Any]] = None,
) -> Optional[models.TaskRun]:
    query: Select[Any] = create_query(
        model=models.TaskRun,
        filters=filters or {},
        eager_load=["task", "workflow_run.workflow_revision.workflow"],
    )
    result = await db.execute(query)

    return result.scalars().first()


async def get_task_run_by_workflow_run_and_task_title(
    db: AsyncSession, workflow_run_id: int, task_title: str
) -> Optional[models.TaskRun]:
    query: Select[Any] = create_query(
        model=models.TaskRun,
        filters={"workflow_run_id": workflow_run_id, "task.title": task_title},
        eager_load=["task"],
    )
    result = await db.execute(query)
    return result.scalars().first()


async def create_or_update_task_run(
    db: AsyncSession,
    task_run_update: schemas.TaskRunUpdate,
    workflow_run_id: int,
) -> models.TaskRun:
    logger.debug(
        "create_or_update_task_run workflow_run_id=%s task_title=%s external_id=%s status=%s",
        workflow_run_id,
        task_run_update.task_title,
        task_run_update.external_id,
        task_run_update.lifecycle_status,
    )
    # check if task run already exists

    db_task_run = await get_task_run_by_workflow_run_and_task_title(
        db, workflow_run_id, task_run_update.task_title
    )
    if db_task_run:
        logger.debug("updating existing task run id=%s", db_task_run.id)
        # update existing task run
        db_task_run = await update_task_run_lifecycle(
            db,
            task_run_id=int(getattr(db_task_run, "id")),
            lifecycle_status=task_run_update.lifecycle_status,
        )
    else:
        logger.info(
            "Creating TaskRun workflow_run_id=%s task_title=%s external_id=%s status=%s",
            workflow_run_id,
            task_run_update.task_title,
            task_run_update.external_id,
            task_run_update.lifecycle_status,
        )
        # get workflow run
        workflow_run = await get_workflow_run(db, filters={"id": workflow_run_id})

        if not workflow_run:
            logger.error(f"WorkflowRun {workflow_run_id} not found")
            raise ValueError(f"WorkflowRun {workflow_run_id} not found")

        logger.debug(
            "workflow_run.id=%s workflow_revision_id=%s",
            workflow_run.id,
            workflow_run.workflow_revision_id,
        )

        # get task from title
        db_task = await get_task(
            db,
            filters={
                "title": task_run_update.task_title,
                "workflow_revision_id": workflow_run.workflow_revision_id,
            },
        )
        if not db_task:
            logger.error(
                "Task not found for TaskRun creation workflow_run_id=%s task_title=%s external_id=%s",
                workflow_run_id,
                task_run_update.task_title,
                task_run_update.external_id,
            )
            raise ValueError(f"Task with title {task_run_update.task_title} not found")

        # create new task run
        db_task_run = await create_task_run(
            db,
            schemas.TaskRunCreate(
                task_id=db_task.id,
                task_title=task_run_update.task_title,
                lifecycle_status=task_run_update.lifecycle_status,
                external_id=task_run_update.external_id,
                workflow_run_id=workflow_run_id,
            ),
        )

    return db_task_run


async def create_task_run(
    db: AsyncSession,
    task_run: schemas.TaskRunCreate,
) -> models.TaskRun:
    db_task_run = models.TaskRun(
        task_id=task_run.task_id,
        workflow_run_id=task_run.workflow_run_id,
        external_id=task_run.external_id,
        lifecycle_status=(
            schemas.TaskRunStatus.CREATED
            if task_run.lifecycle_status == ""
            else task_run.lifecycle_status
        ),
    )
    db.add(db_task_run)
    await db.commit()
    await db.refresh(db_task_run)
    return db_task_run


async def update_task_run_lifecycle(
    db: AsyncSession, task_run_id: int, lifecycle_status: str
) -> models.TaskRun:
    result = await db.execute(
        select(models.TaskRun).filter(models.TaskRun.id == task_run_id)
    )
    db_task_run = result.scalars().first()
    if not db_task_run:
        logger.error(f"Failed to update TaskRun {task_run_id=}")
        raise ValueError("Failed to update TaskRun")
    db_task_run.lifecycle_status = lifecycle_status
    await db.commit()
    await db.refresh(db_task_run)
    return db_task_run
