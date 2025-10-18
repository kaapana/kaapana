import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.encoders import jsonable_encoder

from app import crud, schemas
from app.api.v1.services.errors import *
from app.adapters import get_workflow_engine

logger = logging.getLogger(__name__)


async def get_workflows(
    db: AsyncSession,
    skip: int,
    limit: int,
    order_by: Optional[str],
    order: Optional[str],
    id: Optional[int],
) -> List[schemas.Workflow]:
    filters = {"id": id} if id else {}
    workflows = await crud.get_workflows(
        db, skip=skip, limit=limit, order_by=order_by, order=order, filters=filters
    )
    if not workflows:
        logger.warning(f"No workflows found with filters: {filters}")
        return []
    return workflows


async def create_workflow(
    db: AsyncSession,
    workflow: schemas.WorkflowCreate,
) -> schemas.Workflow:
    db_workflow = await crud.create_workflow(db, workflow=workflow)
    if not db_workflow:
        logger.error(f"Failed to create workflow: {workflow}")
        raise InternalError("Failed to create workflow")
    logger.info(f"Created workflow: {db_workflow.title} v{db_workflow.version}")

    # submit the workflow to the engine and get tasks
    engine = get_workflow_engine(workflow.workflow_engine)
    await engine.submit_workflow(workflow=db_workflow)
    tasks = await engine.get_workflow_tasks(workflow=db_workflow)

    # create tasks in the db
    for task_create in tasks:
        t = await crud.create_task(db=db, task=task_create, workflow_id=db_workflow.id)
        logger.info(f"Created task {t.title} for workflow: {workflow.title}")

    # after all tasks are created, link downstream tasks
    for task in tasks:
        db_task = await crud.get_tasks(
            db,
            filters={
                "title": task.title,
                "workflow.title": db_workflow.title,
                "workflow.version": db_workflow.version,
            },
            single=True,
        )
        if not db_task:
            logger.warning(
                f"Failed to find task {task.title} for workflow: {db_workflow.title} v{db_workflow.version} to link downstream tasks"
            )
            continue

        # get all downstream tasks of task
        for ds_title in task.downstream_task_titles:
            ds_task = await crud.get_tasks(
                db,
                filters={
                    "title": ds_title,
                    "workflow.title": db_workflow.title,
                    "workflow.version": db_workflow.version,
                },
                single=True,
            )
            if not ds_task:
                logger.error(
                    f"Failed to find downstream task {ds_title} for workflow: {db_workflow.title} v{db_workflow.version} to link downstream tasks"
                )
                continue
            # add link in the db
            await crud.add_downstream_task(
                db, task_id=db_task.id, downstream_task_id=ds_task.id
            )
            logger.info(
                f"Added downstream task {ds_task.title} to task {db_task.title}"
            )

    return db_workflow


async def get_workflow_by_title(
    db: AsyncSession,
    title: str,
    latest: bool,
    order_by: Optional[str],
    order: Optional[str],
) -> List[schemas.Workflow]:
    limit = 1 if latest else 100
    workflows = await crud.get_workflows(
        db, filters={"title": title}, order_by="version", order="desc", limit=limit
    )
    if not workflows:
        logger.error(f"Workflow with {title=} not found")
        raise NotFoundError("Workflow not found")
    return workflows


async def get_workflow_by_title_and_version(
    db: AsyncSession, title: str, version: int
) -> schemas.Workflow:
    workflow = await crud.get_workflows(
        db, filters={"title": title, "version": version}, single=True
    )
    if not workflow:
        logger.error(f"Workflow with {title=} and {version=} not found")
        raise NotFoundError("Workflow not found")
    return workflow


async def delete_workflow(db: AsyncSession, title: str, version: int):
    workflow = await crud.get_workflows(
        db, filters={"title": title, "version": version}, single=True
    )
    success = await crud.delete_workflow(db, workflow) if workflow else False
    # TODO: also delete tasks associated with the workflow, but this creates orphaned task runs
    if not success:
        logger.error(f"Failed to delete workflow with {title=} and {version=}")
        raise NotFoundError("Workflow not found")


async def get_workflow_tasks(
    db: AsyncSession, title: str, version: int
) -> List[schemas.Task]:
    workflow = await crud.get_workflows(
        db, filters={"title": title, "version": version}, single=True
    )
    if not workflow:
        logger.error(f"Workflow with {title=} and {version=} not found")
        raise NotFoundError("Workflow not found")

    # get tasks
    tasks = await crud.get_tasks(db, filters={"workflow_id": workflow.id})
    if not tasks:
        logger.warning(f"No tasks found for workflow with {title=} and {version=}")
        return []

    # append downstream task ids to each task
    res = []
    for t in tasks:
        task_data = jsonable_encoder(t)
        task_data["downstream_task_ids"] = [
            dt.downstream_task_id for dt in t.downstream_tasks
        ]
        res.append(schemas.Task(**task_data))
    return res


async def get_task(
    db: AsyncSession, title: str, version: int, task_title: str
) -> schemas.Task:
    task = await crud.get_tasks(
        db,
        filters={
            "title": task_title,
            "workflow.title": title,
            "workflow.version": version,
        },
        single=True,
    )
    if not task:
        logger.error(
            f"Task with {task_title=} for workflow with {title=} and {version=} not found"
        )
        raise NotFoundError("Task not found")

    # append downstream task ids
    task_data = jsonable_encoder(task)
    task_data["downstream_task_ids"] = [
        dt.downstream_task_id for dt in task.downstream_tasks
    ]
    return schemas.Task(**task_data)
