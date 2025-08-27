import logging
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.dependencies import (
    get_async_db,
    get_forwarded_headers,
)
from app import crud, schemas

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
    logger.debug("Creating workflow: %s", workflow)
    db_workflow = await crud.create_workflow(db, workflow=workflow)
    response.headers["Location"] = (
        f"/workflows/{db_workflow.title}/{db_workflow.version}"
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
    tasks = await crud.get_tasks_of_workflow(db, workflow_id=db_workflow.id)
    return tasks


@router.get(
    "/workflows/{title}/{version}/tasks/{task_title}", response_model=schemas.Task
)
async def get_task(task_id: int, db: AsyncSession = Depends(get_async_db)):
    db_task = await crud.get_tasks(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task
