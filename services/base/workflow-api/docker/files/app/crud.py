import logging
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from . import models, schemas
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from typing import Optional, Type, List, Union, Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def create_query(
    db: AsyncSession,
    model: Type[Any],
    filters: Optional[Dict[str, Any]] = None,
    eager_load: Optional[List[str]] = None,
    order_by: Optional[Any] = None,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
) -> Union[Any, List[Any], None]:
    """
    Generic query function for SQLAlchemy models using AsyncSession.

    Parameters:
    - db: SQLAlchemy AsyncSession
    - model: SQLAlchemy ORM model
    - filters: Dict of column_name -> value
    - eager_load: List of relationship names to eager load (flat only)
    - order_by: SQLAlchemy ordering expression
    - skip: Offset for pagination
    - limit: Limit for pagination

    Returns:
    - SQLAlchemy query object
    """
    query = select(model)

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

    return query


async def get_workflows(
    db: AsyncSession,
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    order: Optional[str] = "desc",
    skip: int = 0,
    limit: int = 100,
    single: bool = False,
) -> Union[List[models.Workflow], models.Workflow]:
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
        db=db,
        model=models.Workflow,
        filters=filters or {},
        eager_load=["tasks"],
        order_by=order_by_exp,
        skip=skip,
        limit=limit,
    )
    result = await db.execute(query)
    return result.scalars().first() if single else result.scalars().all()


async def create_workflow(
    db: AsyncSession, workflow: schemas.WorkflowCreate
) -> models.Workflow:
    # get version of workflow
    # NOTE: no need to lock while determining version -> UniqueConstraint(title, version) raises IntegrityError on conflict
    stmt = select(func.max(models.Workflow.version)).filter_by(title=workflow.title)
    result = await db.execute(stmt)
    max_version = result.scalar() or 0
    new_version = max_version + 1

    # get config_definition as json
    config_definition = None
    if workflow.config_definition:
        config_definition = workflow.config_definition.model_dump()

    # add labels if they don't already exist
    db_labels = []
    for label in workflow.labels:
        stmt = select(models.Label).where(
            models.Label.key == label.key, models.Label.value == label.value
        )
        result = await db.execute(stmt)
        db_label = result.scalars().first()
        if not db_label:
            db_label = models.Label(key=label.key, value=label.value)
        db_labels.append(db_label)

    # create workflow object
    db_workflow = models.Workflow(
        title=workflow.title,
        workflow_engine=workflow.workflow_engine,
        definition=workflow.definition,
        config_definition=config_definition,
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
    filters: dict = {},
    order_by=None,
    skip: int = 0,
    limit: int = 100,
    single: bool = False,
) -> Union[List[models.WorkflowRun], models.WorkflowRun]:
    """
    Generic function to get workflow runs with optional project filtering.
    """

    query: Any = create_query(
        db=db,
        model=models.WorkflowRun,
        filters=filters,
        eager_load=["task_runs", "workflow"],
        order_by=order_by or models.WorkflowRun.id.desc(),
        skip=skip,
        limit=limit,
    )

    result = await db.execute(query)
    return result.scalars().first() if single else result.scalars().all()


async def create_workflow_run(
    db: AsyncSession, workflow_run: schemas.WorkflowRunCreate, workflow_id: int
):
    # add labels if they don't already exist
    db_labels = []
    for label in workflow_run.labels:
        stmt = select(models.Label).where(
            models.Label.key == label.key, models.Label.value == label.value
        )
        result = await db.execute(stmt)
        db_label = result.scalars().first()
        if not db_label:
            db_label = models.Label(key=label.key, value=label.value)
        db_labels.append(db_label)

    db_workflow_run = models.WorkflowRun(
        workflow_id=workflow_id, config=workflow_run.config, labels=db_labels
    )

    db.add(db_workflow_run)
    await db.commit()
    await db.refresh(db_workflow_run)

    return db_workflow_run


async def update_workflow_run(
    db: AsyncSession, run_id: int, workflow_run_update: schemas.WorkflowRunUpdate
) -> models.WorkflowRun | None:
    result = await db.execute(
        select(models.WorkflowRun).filter(models.WorkflowRun.id == run_id)
    )
    db_workflow_run = result.scalars().first()
    if not db_workflow_run:
        return None

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
    single: bool = False,
) -> Union[List[models.Task], models.Task]:
    logger.info(
        f"Getting tasks with filters: {filters}, order_by: {order_by}, order: {order}, skip: {skip}, limit: {limit}, single: {single}"
    )
    # construct order_by expression
    order_by_exp = models.Task.id.desc()
    if order_by:
        order_col = getattr(models.Task, order_by, None)
        if order_col is not None:
            order_by_exp = order_col.asc() if order == "asc" else order_col.desc()

    query = create_query(
        db=db,
        model=models.Task,
        filters=filters or {},
        order_by=order_by_exp,
        eager_load=["downstream_tasks"],
        skip=skip,
        limit=limit,
    )
    result = await db.execute(query)

    return result.scalars().first() if single else result.scalars().all()


async def create_task(db: AsyncSession, task: schemas.TaskCreate, workflow_id: int):
    logger.info(f"Creating task {task.display_name} for workflow_id {workflow_id}")

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


async def get_task_runs_of_workflow_run(db: AsyncSession, workflow_run_id: int):
    result = await db.execute(
        select(models.TaskRun)
        .filter(models.TaskRun.workflow_run_id == workflow_run_id)
        .options(selectinload(models.TaskRun.task))
    )
    return result.scalars().all()


async def get_task_run(
    db: AsyncSession,
    filters: Optional[Dict[str, Any]] = None,
):
    result = await db.execute(
        select(models.TaskRun).filter(models.TaskRun.id == task_run_id)
    )
    return result.scalars().first()


async def get_task_run_by_workflow_run_and_task(
    db: AsyncSession, workflow_run_id: int, task_id: int
):
    query = create_query(
        db=db,
        model=models.TaskRun,
        filters={"workflow_run_id": workflow_run_id, "task_id": task_id},
        eager_load=["task"],
    )
    result = await db.execute(query)
    return result.scalars().first()


async def create_task_run(
    db: AsyncSession,
    task_run: schemas.TaskRunCreate,
    task_id: int,
    workflow_run_id: int,
):
    db_task_run = models.TaskRun(
        task_id=task_id,
        workflow_run_id=workflow_run_id,
    )
    db.add(db_task_run)
    await db.commit()
    await db.refresh(db_task_run)
    return db_task_run


async def update_task_run_lifecycle(
    db: AsyncSession, task_run_id: int, lifecycle_status: str
):
    result = await db.execute(
        select(models.TaskRun).filter(models.TaskRun.id == task_run_id)
    )
    db_task_run = result.scalars().first()
    if db_task_run:
        db_task_run.lifecycle_status = lifecycle_status
        await db.commit()
        await db.refresh(db_task_run)
        return db_task_run
    return None
