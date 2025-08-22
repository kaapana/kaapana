from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
import json
from app.dependencies import (
    get_async_db,
    get_forwarded_headers,
)
from app import crud, schemas, models
from typing import Dict, Any

router = APIRouter()

# TODO: check which endpoints are needed, remove unused ones

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
    id: int = None,
    db: AsyncSession = Depends(get_async_db),
):
    filters = {"id": id} if id else {}
    workflows = await crud.get_workflows(db, skip=skip, limit=limit, filters=filters)
    print([m.__dict__ for m in workflows])
    return workflows


@router.post("/workflows", response_model=schemas.Workflow, status_code=201)
async def create_workflow(
    workflow: schemas.WorkflowCreate,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
):
    workflow.config_definition = jsonable_encoder(workflow.config_definition)
    workflow.labels = jsonable_encoder(workflow.labels)
    db_workflow = await crud.create_workflow(db, workflow=workflow)
    response.headers["Location"] = f"/workflows/{workflow.title}/{db_workflow.version}"
    return db_workflow


@router.get("/workflows/{title}", response_model=List[schemas.Workflow])
async def get_workflow_versions(
    title: str,
    latest: bool = False,
    db: AsyncSession = Depends(get_async_db),
):
    filters = {"title": title}
    limit = 1 if latest else 100
    db_workflows = await crud.get_workflows(
        db,
        filters={"title": title},
        order_by=models.Workflow.version.desc(),
        limit=limit,
    )
    if not db_workflows:
        raise HTTPException(
            status_code=404, detail="No versions found for this workflow title"
        )
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
            status_code=404, detail="Workflow not found, cannot get tasks"
        )
    tasks = await crud.get_tasks_by_workflow(db, workflow_id=db_workflow.id)
    return tasks


@router.get("/workflows/{title}/{version}/tasks", response_model=schemas.Task)
async def get_tasks(task_id: int, db: AsyncSession = Depends(get_async_db)):
    db_task = await crud.get_tasks(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found!")
    return db_task


@router.get(
    "/workflows/{title}/{version}/tasks/{task_title}", response_model=schemas.Task
)
async def get_tasks(task_id: int, db: AsyncSession = Depends(get_async_db)):
    db_task = await crud.get_tasks(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found!")
    return db_task
