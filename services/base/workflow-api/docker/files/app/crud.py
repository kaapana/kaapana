from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from . import models, schemas
from sqlalchemy import select, distinct, func
from sqlalchemy.orm import selectinload

def filter_query(query: select, model: type, filter_conditions: dict) -> select:
    """
    Apply filter conditions to the query based on the model's attributes.
    """
    for attr, value in filter_conditions.items():
        query = query.filter(getattr(model, attr) == value)
    return query

def filter_by_project(query: select, model: type, project_id: UUID) -> select:
    return query.filter(getattr(model, "project_id") == project_id)

# CRUD for Workflow
async def get_workflow(db: AsyncSession, project_id: UUID, workflow_id: int):
    #query = filter_query(select(models.Workflow) {'id': workflow_id})
    query = select(models.Workflow).filter(models.Workflow.id == workflow_id)
    query = filter_by_project(query, models.Workflow, project_id)
    result = await db.execute(query)
    return result.scalars().first()

async def get_workflows(db: AsyncSession, project_id: UUID, skip: int = 0, limit: int = 100):
    result = await db.execute(
        select(models.Workflow)
        .filter(models.Workflow.project_id == project_id)
        .options(selectinload(models.Workflow.tasks)) # <--- load also tasks
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_workflow_by_identifier_and_version(db: AsyncSession, project_id: UUID, identifier: str, version: int):
    query = select(models.Workflow).filter(
            models.Workflow.identifier == identifier,
            models.Workflow.version == version
        )
    query = filter_by_project(query, models.Workflow, project_id)
    result = await db.execute(query)
    return result.scalars().first()

async def get_latest_workflow_by_identifier(db: AsyncSession, project_id: UUID, identifier: str):
    query = (
        select(models.Workflow)
        .filter(models.Workflow.identifier == identifier)
        .order_by(models.Workflow.version.desc())
        .limit(1)
    )
    query = filter_by_project(query, models.Workflow, project_id)
    result = await db.execute(query)
    return result.scalars().first()

async def get_workflow_versions(db: AsyncSession, project_id: UUID, identifier: str):
    query = (select(models.Workflow)
        .filter(models.Workflow.identifier == identifier)
        .order_by(models.Workflow.version)
    )
    query = filter_by_project(query, models.Workflow, project_id)
    result = await db.execute(query)
    return result.scalars().all()


async def create_workflow(db: AsyncSession, project_id: UUID, workflow: schemas.WorkflowCreate):
    #TODO lock while determining version ?
    stmt = select(func.max(models.Workflow.version)).filter_by(identifier=workflow.identifier)
    result = await db.execute(stmt)
    max_version = result.scalar()
    new_version = (max_version or 0) + 1
    print(workflow)
    print(f"Creating workflow for project {project_id} with identifier {workflow.identifier}")
    db_workflow = models.Workflow(
        project_id=project_id,
        identifier=workflow.identifier,
        definition=workflow.definition,
        version=new_version,
        config_definition=workflow.config_definition
        )
    db.add(db_workflow)
    await db.commit()
    await db.refresh(db_workflow)
    ## also load tasks?
    await db_workflow.awaitable_attrs.tasks # This uses the asyncio-compatible attribute loader

    return db_workflow

async def delete_workflow(db: AsyncSession, project_id: UUID, workflow_id: int):

    query = select(models.Workflow).filter(models.Workflow.id == workflow_id)
    query = filter_by_project(query, models.Workflow, project_id)
    result = await db.execute(query)
    db_workflow = result.scalars().first()
    if db_workflow:
        await db.delete(db_workflow)
        await db.commit()
        return True
    #TODO : Also delete related UI schema, 
    return False

# CRUD for WorkflowRun
async def get_workflow_run(db: AsyncSession, workflow_run_id: int):
    result = await db.execute(select(models.WorkflowRun).filter(models.WorkflowRun.id == workflow_run_id))
    return result.scalars().first()

async def get_workflow_runs(db: AsyncSession, project_id: UUID, skip: int = 0, limit: int = 100, dataset: Optional[str] = None):
    query = select(models.WorkflowRun)
    query = query.filter(models.WorkflowRun.workflow.has(models.Workflow.project_id == project_id))
    if dataset:
        # This filtering logic might need refinement based on how labels are stored
        query = query.filter(cast(models.WorkflowRun.config['dataset'], String) == dataset)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def create_workflow_run(db: AsyncSession, workflow_run: schemas.WorkflowRunCreate, workflow_id: int):
    db_workflow_run = models.WorkflowRun(
        workflow_id=workflow_id,
        config=workflow_run.config,
        labels=workflow_run.labels
    )
    db.add(db_workflow_run)
    await db.commit()
    await db.refresh(db_workflow_run)
    return db_workflow_run

async def update_workflow_run_lifecycle(db: AsyncSession, workflow_run_id: int, lifecycle_status: str):
    result = await db.execute(select(models.WorkflowRun).filter(models.WorkflowRun.id == workflow_run_id))
    db_workflow_run = result.scalars().first()
    if db_workflow_run:
        db_workflow_run.lifecycle_status = lifecycle_status
        await db.commit()
        await db.refresh(db_workflow_run)
        return db_workflow_run
    return None

async def cancel_workflow_run(db: AsyncSession, workflow_run_id: int):
    result = await db.execute(select(models.WorkflowRun).filter(models.WorkflowRun.id == workflow_run_id))
    db_workflow_run = result.scalars().first()
    if db_workflow_run:
        db_workflow_run.is_canceled = True
        await db.commit()
        await db.refresh(db_workflow_run)
        return db_workflow_run
    return None


# CRUD for Task

#not used right now
async def get_task(db: AsyncSession, task_id: int):
    result = await db.execute(select(models.Task).filter(models.Task.id == task_id))
    return result.scalars().first()

async def get_tasks_by_workflow(db: AsyncSession, workflow_id: int):
    result = await db.execute(select(models.Task).filter(models.Task.workflow_id == workflow_id))
    return result.scalars().all()

async def create_task(db: AsyncSession, task: schemas.TaskCreate, workflow_id: int):
    db_task = models.Task(
        workflow_id=workflow_id,
        task_display_name=task.task_display_name,
        type=task.type,
        input_tasks_ids=task.input_tasks_ids,
        output_tasks_ids=task.output_tasks_ids
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

# CRUD for TaskRun
async def get_task_run(db: AsyncSession, task_run_id: int):
    result = await db.execute(select(models.TaskRun).filter(models.TaskRun.id == task_run_id))
    return result.scalars().first()

async def get_task_run_by_workflow_run_and_task(db: AsyncSession, workflow_run_id: int, task_id: int):
    result = await db.execute(
        select(models.TaskRun).filter(
            models.TaskRun.workflow_run_id == workflow_run_id,
            models.TaskRun.task_id == task_id
        )
    )
    return result.scalars().first()

async def create_task_run(db: AsyncSession, task_run: schemas.TaskRunCreate, task_id: int, workflow_run_id: int):
    db_task_run = models.TaskRun(
        task_id=task_id,
        workflow_run_id=workflow_run_id,
        lifecycle_status=task_run.lifecycle_status
    )
    db.add(db_task_run)
    await db.commit()
    await db.refresh(db_task_run)
    return db_task_run

async def update_task_run_lifecycle(db: AsyncSession, task_run_id: int, lifecycle_status: str):
    result = await db.execute(select(models.TaskRun).filter(models.TaskRun.id == task_run_id))
    db_task_run = result.scalars().first()
    if db_task_run:
        db_task_run.lifecycle_status = lifecycle_status
        await db.commit()
        await db.refresh(db_task_run)
        return db_task_run
    return None

# CRUD for WorkflowUISchema
async def create_workflow_ui_schema(db: AsyncSession, ui_schema: schemas.WorkflowUISchemaCreate, workflow_identifier: str, workflow_version: int):
    db_ui_schema = models.WorkflowUISchema(
        workflow_identifier=workflow_identifier,
        workflow_version=workflow_version,
        schema_definition=ui_schema.schema_definition
    )
    db.add(db_ui_schema)
    await db.commit()
    await db.refresh(db_ui_schema)
    return db_ui_schema

async def get_latest_workflow_ui_schema(db: AsyncSession, identifier: str):
    result = await db.execute(
        select(models.WorkflowUISchema)
        .filter(models.WorkflowUISchema.workflow_identifier == identifier)
        .order_by(models.WorkflowUISchema.workflow_version.desc())
        .limit(1)
    )
    return result.scalars().first()

async def get_workflow_ui_schema(db: AsyncSession, workflow_identifier: str, workflow_version: int):
    result = await db.execute(select(models.WorkflowUISchema).filter(models.WorkflowUISchema.workflow_identifier == workflow_identifier, models.WorkflowUISchema.workflow_version == workflow_version))
    return result.scalars().first()

async def get_workflow_ui_schemas_per_project(db: AsyncSession, project_id: UUID):
    query = select(models.WorkflowUISchema).join(models.Workflow, models.WorkflowUISchema.workflow_identifier == models.Workflow.identifier)
    query = query.filter(models.Workflow.project_id == project_id)
    result = await db.execute(query)
    return result.scalars().all()

# get get_latest_workflow_ui_schemas_per_project
async def get_latest_workflow_ui_schemas_per_project(db: AsyncSession, project_id: UUID):
    subquery = (
        select(
            models.WorkflowUISchema.workflow_identifier,
            models.WorkflowUISchema.workflow_version,
        )
        .join(
            models.Workflow,
            models.WorkflowUISchema.workflow_identifier == models.Workflow.identifier,
        )
        .filter(models.Workflow.project_id == project_id)
        .order_by(
            models.WorkflowUISchema.workflow_identifier,
            models.WorkflowUISchema.workflow_version.desc(),
        )
        .distinct(models.WorkflowUISchema.workflow_identifier)
        .subquery()
    )

    query = (
        select(models.WorkflowUISchema)
        .join(
            subquery,
            (models.WorkflowUISchema.workflow_identifier == subquery.c.workflow_identifier)
            & (models.WorkflowUISchema.workflow_version == subquery.c.workflow_version),
        )
    )

    result = await db.execute(query)
    return result.scalars().all()