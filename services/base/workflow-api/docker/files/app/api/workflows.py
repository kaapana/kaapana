import logging
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.dependencies import (
    get_async_db,
    get_forwarded_headers,  # TODO
)
from app import crud, schemas
from app.adapters import get_workflow_engine


logger = logging.getLogger(__name__)
router = APIRouter()

# WebSocket endpoint for lifecycle updates
# @router.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     try:
#         while True:
#             # Here you would listen for lifecycle updates from your workflow engine
#             # and send them to the connected client.
#             # For now, we'll just keep the connection open.
#             await websocket.receive_text() # Keep connection open
#     except WebSocketDisconnect:
#         print("Client disconnected")


# Workflow Endpoints
@router.get("/workflows", response_model=List[schemas.Workflow])
async def get_workflows(
    skip: int = 0,
    limit: int = 100,
    order_by: Optional[str] = None,  # e.g., "created_at", "version"
    order: Optional[str] = "desc",  # "asc" or "desc"
    id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
):
    logger.debug("Getting workflows with skip=%d, limit=%d, id=%s", skip, limit, id)
    filters = {"id": id} if id else {}
    workflows = await crud.get_workflows(
        db, skip=skip, limit=limit, order_by=order_by, order=order, filters=filters
    )
    if not workflows:
        raise HTTPException(status_code=404, detail="No workflows found")
    return workflows


@router.post("/workflows", response_model=schemas.Workflow, status_code=201)
async def create_workflow(
    workflow: schemas.WorkflowCreate,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
):
    logger.debug(f"Creating workflow: {workflow}")
    db_workflow = await crud.create_workflow(db, workflow=workflow)
    response.headers["Location"] = (
        f"/workflows/{db_workflow.title}/{db_workflow.version}"
    )
    if not db_workflow:
        logger.error(f"Failed to create workflow: {workflow}")
        raise HTTPException(status_code=400, detail="Failed to create workflow")
    logger.info(f"Created workflow: {db_workflow.title} v{db_workflow.version}")

    # get the workflow engine adapter
    engine = get_workflow_engine(workflow_engine=workflow.workflow_engine)
    logger.info(
        f"Using workflow engine: {engine.workflow_engine} for workflow: {workflow.title}"
    )
    # submit the workflow to the engine and get tasks
    await engine.submit_workflow(workflow=db_workflow)
    tasks = await engine.get_workflow_tasks(workflow=db_workflow)

    # create tasks in the database
    for task_create in tasks:
        t = await crud.create_task(
            db=db,
            task=task_create,
            workflow_id=db_workflow.id,
        )
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
            logger.error(
                f"Failed to find task {task.title} for workflow: {db_workflow.title} v{db_workflow.version} to link downstream tasks"
            )
            continue
        for downstream_title in task.downstream_task_titles:
            ds_task = await crud.get_tasks(
                db,
                filters={
                    "title": downstream_title,
                    "workflow.title": db_workflow.title,
                    "workflow.version": db_workflow.version,
                },
                single=True,
            )
            if not ds_task:
                logger.error(
                    f"Failed to find downstream task {downstream_title} for workflow: {db_workflow.title} v{db_workflow.version} to link downstream tasks"
                )
                continue
            logger.info(
                f"Linking task {db_task.title} to downstream task {ds_task.title}"
            )
            await crud.add_downstream_task(
                db, task_id=db_task.id, downstream_task_id=ds_task.id
            )
            logger.info(
                f"Added downstream task {ds_task.title} to task {db_task.title}"
            )

    return db_workflow


@router.get("/workflows/{title}", response_model=List[schemas.Workflow])
async def get_workflow_by_title(
    title: str,
    latest: bool = False,
    order_by: Optional[str] = None,
    order: Optional[str] = "desc",
    db: AsyncSession = Depends(get_async_db),
):
    limit = 1 if latest else 100
    db_workflows = await crud.get_workflows(
        db,
        filters={"title": title},
        order_by="version",
        order="desc",
        limit=limit,
    )
    if not db_workflows:
        logger.error(f"Workflow with {title=} not found")
        raise HTTPException(status_code=404, detail="Workflow not found")
    return db_workflows


@router.get(
    "/workflows/{title}/{version}",
    response_model=schemas.Workflow,
)
async def get_workflow_by_title_and_version(
    title: str,
    version: int,
    db: AsyncSession = Depends(get_async_db),
):
    db_workflow = await crud.get_workflows(
        db,
        filters={
            "title": title,
            "version": version,
        },
        single=True,
    )
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return db_workflow


@router.delete("/workflows/{title}/{version}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    title: str,
    version: int,
    db: AsyncSession = Depends(get_async_db),
):
    db_workflow = await crud.get_workflows(
        db,
        filters={
            "title": title,
            "version": version,
        },
        single=True,
    )
    success = False
    if db_workflow:
        success = await crud.delete_workflow(db, db_workflow)
    # TODO: Also delete
    # related tasks, but not task-runs? But then task-runs would be orphaned?? So maybe not delete tasks?
    # but for sure a delte task endpoint should be implemented
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return


@router.get(
    "/workflows/{title}/{version}/tasks",
    response_model=List[schemas.Task],
)
async def get_workflow_tasks(
    title: str,
    version: int,
    db: AsyncSession = Depends(get_async_db),
):

    db_workflow = await crud.get_workflows(
        db,
        filters={
            "title": title,
            "version": version,
        },
        single=True,
    )
    if db_workflow is None:
        raise HTTPException(
            status_code=404,
            detail="Failed to get tasks of workflow: Workflow not found",
        )
    # get tasks
    db_tasks = await crud.get_tasks(db, filters={"workflow_id": db_workflow.id})
    if db_tasks is None:
        raise HTTPException(status_code=404, detail="Tasks not found")

    # append downstream task ids to each task
    tasks = []
    for db_task in db_tasks:
        ds_ids = [dt.downstream_task_id for dt in db_task.downstream_tasks]
        task = jsonable_encoder(db_task)
        logger.info("adding ds tasks %s to task %s", ds_ids, db_task.title)
        task["downstream_task_ids"] = ds_ids
        tasks.append(schemas.Task(**task))

    return tasks


@router.get(
    "/workflows/{title}/{version}/tasks/{task_title}", response_model=schemas.Task
)
async def get_task(
    title: str,
    version: int,
    task_title: str,
    db: AsyncSession = Depends(get_async_db),
):
    db_task = await crud.get_tasks(
        db,
        filters={
            "title": task_title,
            "workflow.title": title,
            "workflow.version": version,
        },
        single=True,
    )
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # append downstream task ids
    ds_ids = [dt.downstream_task_id for dt in db_task.downstream_tasks]
    task = jsonable_encoder(db_task)
    logger.info("adding ds tasks %s to task %s", ds_ids, db_task.title)
    task["downstream_task_ids"] = ds_ids

    return schemas.Task(**task)
