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
    get_project,
    get_project_id,
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
async def get_workflows_endpoint(
    skip: int = 0,
    limit: int = 100,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):
    workflows = await crud.get_workflows(
        db, filters={"project_id": project_id}, skip=skip, limit=limit
    )
    return workflows


@router.get("/workflows/{id}", response_model=schemas.Workflow)
async def get_workflow_by_id(
    id: int,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):
    db_workflow = await crud.get_workflows(
        db, filters={"project_id": project_id, "id": id}, single=True
    )
    if not db_workflow:
        raise HTTPException(status_code=404, detail="No workflow found")
    return db_workflow


@router.post("/workflows", response_model=schemas.Workflow, status_code=201)
async def create_workflow(
    workflow: schemas.WorkflowCreate,
    response: Response,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):
    workflow.config_definition = jsonable_encoder(workflow.config_definition)
    workflow.labels = jsonable_encoder(workflow.labels)
    db_workflow = await crud.create_workflow(
        db, project_id=project_id, workflow=workflow
    )
    response.headers["Location"] = f"/workflows/{db_workflow.id}"
    return db_workflow


@router.get("/workflows/{identifier}/latest", response_model=schemas.Workflow)
async def get_latest_version_workflow(
    identifier: str,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):
    db_workflow = await crud.get_workflows(
        db,
        filters={"identifier": identifier, "project_id": project_id},
        order_by=models.Workflow.version.desc(),
        limit=1,
        single=True,
    )
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return db_workflow


@router.get("/workflows/{identifier}/versions", response_model=List[schemas.Workflow])
async def get_workflow_versions(
    identifier: str,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):
    db_workflows = await crud.get_workflows(
        db,
        filters={"identifier": identifier, "project_id": project_id},
        order_by=models.Workflow.version.desc(),
    )
    if not db_workflows:
        raise HTTPException(
            status_code=404, detail="No versions found for this workflow identifier"
        )
    return db_workflows


@router.get(
    "/workflows/{identifier}/versions/{version}", response_model=schemas.Workflow
)
async def get_workflow_by_identifier_and_version(
    identifier: str,
    version: int,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):
    db_workflow = await crud.get_workflows(
        db,
        filters={
            "identifier": identifier,
            "version": version,
            "project_id": project_id,
        },
        single=True,
    )
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return db_workflow


@router.delete(
    "/workflows/{identifier}/versions/{version}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_workflow(
    identifier: str,
    version: int,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):
    db_workflow = await crud.get_workflows(
        db,
        filters={
            "identifier": identifier,
            "version": version,
            "project_id": project_id,
        },
        single=True,
    )
    success = False
    if db_workflow:
        is_deleted = await crud.delete_workflow_ui_schema(db, db_workflow.id)
        success = await crud.delete_workflow(db, db_workflow)
    # TODO: Also delete
    # related tasks, but not task-runs? But then task-runs would be orphaned?? So maybe not delete tasks?
    # but for sure a delte task endpoint should be implemented
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return


@router.get(
    "/workflows/{identifier}/versions/{version}/tasks",
    response_model=List[schemas.Task],
)
async def get_workflow_tasks(
    identifier: str,
    version: int,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):

    db_workflow = await crud.get_workflows(
        db,
        filters={
            "identifier": identifier,
            "version": version,
            "project_id": project_id,
        },
        single=True,
    )
    if db_workflow is None:
        raise HTTPException(
            status_code=404, detail="Workflow not found, cannot get tasks"
        )
    tasks = await crud.get_tasks_by_workflow(db, workflow_id=db_workflow.id)
    return tasks


@router.get("/tasks/{task_id}", response_model=schemas.Task)
async def get_tasks(task_id: int, db: AsyncSession = Depends(get_async_db)):
    db_task = await crud.get_tasks(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found!")
    return db_task
