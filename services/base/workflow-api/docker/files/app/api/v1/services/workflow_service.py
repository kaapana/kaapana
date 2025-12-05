import logging
import asyncio
from typing import Any, List, Optional
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from app import crud, schemas
from app.adapters import get_workflow_engine
from app.api.v1.services.errors import InternalError, NotFoundError
from app.api.v1.services.utils import run_in_background_with_retries
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
    if not workflows:
        logger.warning(f"No workflows found with filters: {filters}")
        return []
    return [schemas.Workflow.model_validate(w) for w in workflows]


async def create_workflow(
    db: AsyncSession,
    workflow: schemas.WorkflowCreate,
    token: Optional[str] = None,
) -> schemas.Workflow:
    db_workflow = await crud.create_workflow(db, workflow=workflow)
    if not db_workflow:
        logger.error(f"Failed to create workflow: {workflow}")
        raise InternalError("Failed to create workflow")
    logger.info(f"Created workflow: {db_workflow.title} v{db_workflow.version}")

    engine = get_workflow_engine(workflow.workflow_engine)

    # background task immediately and return the DB object
    asyncio.create_task(
        run_in_background_with_retries(
            _submit_and_parse_workflow_tasks,
            db=db,
            db_workflow=db_workflow,
            engine=engine,
        )
    )

    # return the created workflow immediately before tasks are known
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
        raise NotFoundError("Workflow not found")
    return schemas.Workflow.model_validate(workflow)


async def delete_workflow(db: AsyncSession, title: str, version: int):
    workflow = await crud.get_workflow(db, filters={"title": title, "version": version})
    success = await crud.delete_workflow(db, workflow) if workflow else False
    # workflow is already filtered by removed=False, so removed ones are not returned
    if not success:
        logger.error(f"Failed to delete workflow with {title=} and {version=}")
        raise NotFoundError("Workflow not found")


async def get_workflow_tasks(
    db: AsyncSession, title: str, version: int
) -> List[schemas.Task]:
    workflow = await crud.get_workflow(db, filters={"title": title, "version": version})
    if not workflow:
        logger.error(f"Workflow with {title=} and {version=} not found")
        raise NotFoundError("Workflow not found")

    # get tasks
    tasks = await crud.get_tasks(db, filters={"workflow_id": workflow.id})
    if not tasks:
        logger.warning(f"No tasks found for workflow with {title=} and {version=}")
        raise NotFoundError("Workflow not found")

    # append downstream task ids to each task and convert to schema
    res = []
    for t in tasks:
        task_data = jsonable_encoder(t)
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
        raise NotFoundError("Task not found")

    # append downstream task ids
    task_data = jsonable_encoder(task)
    task_data["downstream_task_ids"] = [
        dt.downstream_task_id for dt in task.downstream_tasks
    ]
    return schemas.Task(**task_data)


async def _submit_and_parse_workflow_tasks(
    db: AsyncSession,
    db_workflow: schemas.Workflow,
    engine: Any,
):
    """
    Submits the DAG file to the engine, polls for its existence,
    and then fetches and links tasks in the local database.
    This function should be wrapped in run_in_background_with_retries.
    """
    schema_workflow = schemas.Workflow.model_validate(db_workflow)

    # submit the DAG file
    await engine.submit_workflow(workflow=schema_workflow)

    # get workflow tasks from the engine
    tasks: List[schemas.TaskCreate] = await engine.get_workflow_tasks(
        workflow=schema_workflow
    )

    # create tasks in the database
    db_tasks = {}
    for task_create in tasks:
        t = await crud.create_task(db=db, task=task_create, workflow_id=db_workflow.id)
        db_tasks[t.title] = t 
        logger.info(f"Created task {t.title} for workflow: {db_workflow.title}")

    # link downstream tasks
    for task_from_engine in tasks:
        db_task = db_tasks.get(task_from_engine.title)

        if not db_task:
            logger.warning(
                f"Failed to find task {task_from_engine.title} in newly created tasks."
            )
            continue

        for ds_title in task_from_engine.downstream_task_titles:
            ds_task = db_tasks.get(ds_title)

            if not ds_task:
                logger.error(
                    f"Failed to find downstream task {ds_title} to link to {db_task.title}."
                )
                continue

            # add link in the db
            await crud.add_downstream_task(
                db, task_id=db_task.id, downstream_task_id=ds_task.id
            )
            logger.info(
                f"Added downstream task {ds_task.title} to task {db_task.title}"
            )

    # commit session at the end
    await db.commit()
    logger.info(
        f"Successfully created and parsed tasks for workflow {db_workflow.title}."
    )
