import logging
from typing import List, Optional

from app import crud, schemas
from app.adapters import get_workflow_engine
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

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
    return [schemas.Workflow.model_validate(w) for w in workflows]


async def create_workflow(
    db: AsyncSession,
    workflow: schemas.WorkflowCreate,
) -> schemas.Workflow:
    db_workflow = await crud.create_workflow(db, workflow=workflow)
    if not db_workflow:
        logger.error(f"Failed to create workflow: {workflow}")
        raise HTTPException(status_code=400, detail="Failed to create workflow")
    logger.info(f"Created workflow: {db_workflow.title} v{db_workflow.version}")

    # submit the workflow to the engine and get tasks
    engine = get_workflow_engine(workflow.workflow_engine)
    # convert ORM workflow to schema for engine adapters that expect schema types
    schema_workflow = schemas.Workflow.model_validate(db_workflow)
    await engine.submit_workflow(workflow=schema_workflow)
    tasks = await engine.get_workflow_tasks(workflow=schema_workflow)

    # create tasks in the db
    for task_create in tasks:
        t = await crud.create_task(db=db, task=task_create, workflow_id=db_workflow.id)
        logger.info(f"Created task {t.title} for workflow: {workflow.title}")

    # after all tasks are created, link downstream tasks
    for task in tasks:
        db_task = await crud.get_task(
            db,
            filters={
                "title": task.title,
                "workflow.title": db_workflow.title,
                "workflow.version": db_workflow.version,
            },
        )
        if not db_task:
            logger.warning(
                f"Failed to find task {task.title} for workflow: {db_workflow.title} v{db_workflow.version} to link downstream tasks"
            )
            continue

        # get all downstream tasks of task
        for ds_title in task.downstream_task_titles:
            ds_task = await crud.get_task(
                db,
                filters={
                    "title": ds_title,
                    "workflow.title": db_workflow.title,
                    "workflow.version": db_workflow.version,
                },
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

    return schemas.Workflow.model_validate(db_workflow)


async def get_workflow_by_title(
    db: AsyncSession,
    title: str,
    latest: bool,
) -> List[schemas.Workflow]:
    limit = 1 if latest else 100
    workflows = await crud.get_workflows(
        db, filters={"title": title}, order_by="version", order="desc", limit=limit
    )
    if not workflows:
        logger.error(f"Workflow with {title=} not found")
        raise HTTPException(status_code=404, detail="Workflow not found")
    # convert each ORM Workflow to schema
    return [schemas.Workflow.model_validate(w) for w in workflows]


async def get_workflow_by_title_and_version(
    db: AsyncSession, title: str, version: int
) -> schemas.Workflow:
    workflow = await crud.get_workflow(db, filters={"title": title, "version": version})
    if not workflow:
        logger.error(f"Workflow with {title=} and {version=} not found")
        raise HTTPException(status_code=404, detail="Workflow not found")
    return schemas.Workflow.model_validate(workflow)


async def delete_workflow(db: AsyncSession, title: str, version: int):
    workflow = await crud.get_workflow(db, filters={"title": title, "version": version})
    success = await crud.delete_workflow(db, workflow) if workflow else False
    # TODO: also delete tasks associated with the workflow, but this creates orphaned task runs
    if not success:
        logger.error(f"Failed to delete workflow with {title=} and {version=}")
        raise HTTPException(status_code=404, detail="Workflow not found")


async def get_workflow_tasks(
    db: AsyncSession, title: str, version: int
) -> List[schemas.Task]:
    workflow = await crud.get_workflow(db, filters={"title": title, "version": version})
    if not workflow:
        logger.error(f"Workflow with {title=} and {version=} not found")
        raise HTTPException(status_code=404, detail="Workflow not found")

    # get tasks
    tasks = await crud.get_tasks(db, filters={"workflow_id": workflow.id})
    if not tasks:
        logger.info(f"No tasks found for workflow with {title=} and {version=}")
        raise HTTPException(status_code=404, detail="Tasks not found")

    # append downstream task ids to each task and convert to schema
    res = []
    for t in tasks:
        # build a simple dict from ORM attributes instead of walking the whole
        # SQLAlchemy object graph with jsonable_encoder (which can recurse).
        task_data = {
            "id": t.id,
            "workflow_id": t.workflow_id,
            "title": t.title,
            "display_name": t.display_name,
            "type": t.type,
        }
        task_data["downstream_task_ids"] = [
            dt.downstream_task_id for dt in t.downstream_tasks
        ]
        res.append(schemas.Task.model_validate(task_data))
    return res


async def get_task(
    db: AsyncSession, title: str, version: int, task_title: str
) -> schemas.Task:
    task = await crud.get_task(
        db,
        filters={
            "title": task_title,
            "workflow.title": title,
            "workflow.version": version,
        },
    )
    if not task:
        logger.error(
            f"Task with {task_title=} for workflow with {title=} and {version=} not found"
        )
        raise HTTPException(status_code=404, detail="Task not found")

    # append downstream task ids (explicit fields to avoid recursive encode)
    task_data = {
        "id": task.id,
        "workflow_id": task.workflow_id,
        "title": task.title,
        "display_name": task.display_name,
        "type": task.type,
        "downstream_task_ids": [dt.downstream_task_id for dt in task.downstream_tasks],
    }
    return schemas.Task.model_validate(task_data)
