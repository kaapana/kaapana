from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from . import models, schemas
from sqlalchemy import select, distinct, func
from sqlalchemy.orm import selectinload

from typing import Optional, Type, List, Union, Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert


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

    # Apply direct filters
    if filters:
        for attr, value in filters.items():
            query = query.filter(getattr(model, attr) == value)

    # Apply eager loading (flat only)
    if eager_load:
        for relation in eager_load:
            query = query.options(selectinload(getattr(model, relation)))

    # Apply ordering
    if order_by is not None:
        query = query.order_by(order_by)

    # Apply pagination
    if skip is not None:
        query = query.offset(skip)
    if limit is not None:
        query = query.limit(limit)

    return query


def filter_by_project(query: select, model: type, project_id: UUID) -> select:
    return query.filter(getattr(model, "project_id") == project_id)


async def get_workflows(
    db: AsyncSession,
    filters: dict = None,
    order_by=None,
    skip: int = 0,
    limit: int = 100,
    single: bool = False,
):
    """
    Generic function to get workflows based on filters and parameters.
    Workflows always eager load tasks by default.
    """
    # TODO join labels
    query = create_query(
        db=db,
        model=models.Workflow,
        filters=filters or {},
        eager_load=["tasks"],
        order_by=order_by,
        skip=skip,
        limit=limit,
    )
    result = await db.execute(query)
    return result.scalars().first() if single else result.scalars().all()


async def create_workflow(db: AsyncSession, workflow: schemas.WorkflowCreate):
    # TODO lock while determining version ?
    stmt = select(func.max(models.Workflow.version)).filter_by(title=workflow.title)
    result = await db.execute(stmt)
    max_version = result.scalar()
    new_version = (max_version or 0) + 1
    db_workflow = models.Workflow(
        title=workflow.title,
        definition=workflow.definition,
        version=new_version,
        config_definition=workflow.config_definition,
        labels=workflow.labels,
    )
    db.add(db_workflow)
    await db.commit()
    # get workfow to load realationships:
    workflow = await get_workflows(db=db, filters={"id": db_workflow.id}, single=True)

    return workflow


async def delete_workflow(db: AsyncSession, db_workflow: models.Workflow):
    await db.delete(db_workflow)
    await db.commit()
    return True


# CRUD for WorkflowRun
async def get_workflow_runs(
    db: AsyncSession,
    filters: dict = None,
    project_id: Optional[UUID] = None,
    order_by=None,
    skip: int = 0,
    limit: int = 100,
    single: bool = False,
):
    """
    Generic function to get workflow runs with optional project filtering.
    """

    query = create_query(
        db=db,
        model=models.WorkflowRun,
        filters=filters or {},
        order_by=order_by or models.WorkflowRun.id.desc(),
        skip=skip,
        limit=limit,
    )
    # since nested, don't add to create_query
    query = query.options(
        selectinload(models.WorkflowRun.task_runs).selectinload(models.TaskRun.task)
    )
    # Add project filter if provided
    if project_id:
        query = query.filter(
            models.WorkflowRun.workflow.has(models.Workflow.project_id == project_id)
        )

    result = await db.execute(query)
    return result.scalars().first() if single else result.scalars().all()


async def create_workflow_run(
    db: AsyncSession, workflow_run: schemas.WorkflowRunCreate, workflow_id: int
):
    db_workflow_run = models.WorkflowRun(
        workflow_id=workflow_id, config=workflow_run.config, labels=workflow_run.labels
    )
    db.add(db_workflow_run)
    await db.commit()
    await db.refresh(db_workflow_run)
    return db_workflow_run


async def update_workflow_run(
    db: AsyncSession, run_id: int, workflow_run_update: schemas.WorkflowRunUpdate
):
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


async def get_task_runs_by_workflow_run(db: AsyncSession, workflow_run_id: int):
    result = await db.execute(
        select(models.TaskRun)
        .filter(models.TaskRun.workflow_run_id == workflow_run_id)
        .options(selectinload(models.TaskRun.task))
    )
    return result.scalars().all()


async def get_tasks(db: AsyncSession, task_id: int):
    result = await db.execute(select(models.Task).filter(models.Task.id == task_id))
    return result.scalars().first()


# CRUD for Task

# not used right now


async def get_tasks_by_workflow(db: AsyncSession, workflow_id: int):
    result = await db.execute(
        select(models.Task).filter(models.Task.workflow_id == workflow_id)
    )
    return result.scalars().all()


async def create_task(db: AsyncSession, task: schemas.TaskCreate, workflow_id: int):
    db_task = models.Task(
        workflow_id=workflow_id,
        task_identifier=task.task_identifier,
        display_name=task.display_name,
        type=task.type,
        input_tasks_ids=task.input_tasks_ids,
        output_tasks_ids=task.output_tasks_ids,
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


# CRUD for TaskRun
async def get_task_run(db: AsyncSession, task_run_id: int):
    result = await db.execute(
        select(models.TaskRun).filter(models.TaskRun.id == task_run_id)
    )
    return result.scalars().first()


async def get_task_run_by_workflow_run_and_task(
    db: AsyncSession, workflow_run_id: int, task_id: int
):
    # result = await db.execute(
    #     select(models.TaskRun).filter(
    #         models.TaskRun.workflow_run_id == workflow_run_id,
    #         models.TaskRun.task_id == task_id
    #     )
    # )
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
        lifecycle_status=task_run.lifecycle_status,
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
