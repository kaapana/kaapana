import logging
from typing import Any, Dict, List, Optional, Type, cast

from fastapi.encoders import jsonable_encoder
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models, schemas

logger = logging.getLogger(__name__)


def create_query(
    model: Type[Any],
    filters: Optional[Dict[str, Any]] = None,
    eager_load: Optional[List[str]] = None,
    order_by: Optional[Any] = None,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
) -> Select[Any]:
    """
    Generic query function for SQLAlchemy models using AsyncSession.

    Parameters:
    - model: SQLAlchemy ORM model
    - filters: Dict of column_name -> value
    - eager_load: List of relationship names to eager load (flat only)
    - order_by: SQLAlchemy ordering expression
    - skip: Offset for pagination
    - limit: Limit for pagination

    Returns:
    - SQLAlchemy query object
    """
    query: Select[Any] = select(model)

    # Apply eager loading
    if eager_load:
        for relation in eager_load:
            query = query.options(selectinload(getattr(model, relation)))

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


async def get_workflows(
    db: AsyncSession,
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    order: Optional[str] = "desc",
    skip: int = 0,
    limit: int = 100,
) -> List[models.Workflow]:
    """
    Generic function to get workflows based on filters and parameters.
    Workflows always eager load tasks by default.
    """
    # TODO join labels

    # construct order_by expression
    order_by_exp = models.Workflow.created_at.desc()
    if order_by:
        order_col = getattr(models.Workflow, order_by, None)
        if order_col is not None:
            order_by_exp = order_col.asc() if order == "asc" else order_col.desc()

    query = create_query(
        model=models.Workflow,
        filters=filters or {},
        eager_load=["tasks"],
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
    """
    Generic function to get workflows based on filters and parameters.
    Workflows always eager load tasks by default.
    """
    # TODO join labels

    # construct order_by expression
    order_by_exp = models.Workflow.created_at.desc()

    query = create_query(
        model=models.Workflow,
        filters=filters or {},
        eager_load=["tasks"],
        order_by=order_by_exp,
    )
    result = await db.execute(query)
    return result.scalars().first()


async def create_workflow(
    db: AsyncSession, workflow: schemas.WorkflowCreate
) -> models.Workflow:
    # get version of workflow
    # NOTE: no need to lock while determining version -> UniqueConstraint(title, version) raises IntegrityError on conflict
    version_stmt = select(func.max(models.Workflow.version)).filter_by(
        title=workflow.title
    )
    result = await db.execute(version_stmt)
    max_version = result.scalar() or 0
    new_version = max_version + 1

    # add labels if they don't already exist
    db_labels: List[models.Label] = []
    for label in getattr(workflow, "labels", []) or []:
        stmt: Select[Any] = select(models.Label).where(
            models.Label.key == label.key, models.Label.value == label.value
        )
        result = await db.execute(stmt)
        db_label = cast(Optional[models.Label], result.scalars().first())
        if not db_label:
            db_label = models.Label(key=label.key, value=label.value)
        db_labels.append(db_label)

    # create workflow object
    db_workflow = models.Workflow(
        title=workflow.title,
        workflow_engine=workflow.workflow_engine,
        definition=workflow.definition,
        workflow_parameters=jsonable_encoder(workflow.workflow_parameters),
        version=new_version,
        labels=db_labels,
    )

    db.add(db_workflow)
    await db.commit()
    await db.refresh(
        db_workflow
    )  # ensures db_workflow.labels are fully loaded with lazy="selectin"

    return db_workflow


async def delete_workflow(db: AsyncSession, db_workflow: models.Workflow) -> bool:
    await db.delete(db_workflow)
    await db.commit()
    return True


# CRUD for WorkflowRun
async def get_workflow_runs(
    db: AsyncSession,
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[Any] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.WorkflowRun]:
    """
    Generic function to get workflow runs with optional project filtering.
    """

    query: Select[Any] = create_query(
        model=models.WorkflowRun,
        filters=filters,
        eager_load=["task_runs", "workflow"],
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
    """
    Generic function to get a single workflow run with optional project filtering.
    """

    query: Select[Any] = create_query(
        model=models.WorkflowRun,
        filters=filters or {},
        eager_load=["task_runs", "workflow"],
    )

    result = await db.execute(query)
    return result.scalars().first()


async def create_workflow_run(
    db: AsyncSession, workflow_run: schemas.WorkflowRunCreate, workflow_id: int
) -> models.WorkflowRun:
    # add labels if they don't already exist
    db_labels: List[models.Label] = []
    for label in getattr(workflow_run, "labels", []) or []:
        stmt = select(models.Label).where(
            models.Label.key == label.key, models.Label.value == label.value
        )
        result = await db.execute(stmt)
        db_label = result.scalars().first()
        if not db_label:
            db_label = models.Label(key=label.key, value=label.value)
        db_labels.append(db_label)

    db_workflow_run = models.WorkflowRun(
        workflow_id=workflow_id,
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


# CRUD for Task


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
) -> models.Task:
    query = create_query(
        model=models.Task,
        filters=filters or {},
        eager_load=["downstream_tasks"],
    )
    result = await db.execute(query)
    return result.scalars().first()


async def create_task(
    db: AsyncSession, task: schemas.TaskCreate, workflow_id: int
) -> models.Task:
    logger.info(f"Creating task {task.title} for workflow_id {workflow_id}")

    db_task = models.Task(
        workflow_id=workflow_id,
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
    # check if downstream task already exists
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


# CRUD for TaskRun
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
        eager_load=["task", "workflow_run"],
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
    logger.debug(f"create_or_update_task_run {task_run_update=}, {workflow_run_id=}")
    # check if task run already exists

    db_task_run = await get_task_run_by_workflow_run_and_task_title(
        db, workflow_run_id, task_run_update.task_title
    )
    if db_task_run:
        logger.info(f"updating existing task run {db_task_run.id}")
        # update existing task run
        db_task_run = await update_task_run_lifecycle(
            db,
            task_run_id=int(getattr(db_task_run, "id")),
            lifecycle_status=task_run_update.lifecycle_status,
        )
    else:
        logger.info(f"creating new task run {task_run_update=}")

        # get task from title
        db_task = await get_task(
            db,
            filters={"title": task_run_update.task_title},
        )
        if not db_task:
            logger.error(f"Task with title {task_run_update.task_title} not found")
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
):
    # TODO
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
