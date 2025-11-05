import logging
from typing import List, Optional

from app import schemas
from app.api.v1.services import workflow_service as service
from app.dependencies import get_async_db
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

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


@router.get("/workflows", response_model=List[schemas.Workflow])
async def get_workflows(
    skip: int = 0,
    limit: int = 100,
    order_by: Optional[str] = None,
    order: Optional[str] = "desc",
    id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_workflows(db, skip, limit, order_by, order, id)


@router.post("/workflows", response_model=schemas.Workflow, status_code=201)
async def create_workflow(
    workflow: schemas.WorkflowCreate,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
):
    workflow_res = await service.create_workflow(db, workflow)
    response.headers["Location"] = (
        f"/workflows/{workflow_res.title}/{workflow_res.version}"
    )
    return workflow_res


@router.get("/workflows/{title}", response_model=List[schemas.Workflow])
async def get_workflow_by_title(
    title: str,
    latest: bool = False,
    order_by: Optional[str] = None,
    order: Optional[str] = "desc",
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_workflow_by_title(db, title, latest)


@router.get("/workflows/{title}/{version}", response_model=schemas.Workflow)
async def get_workflow_by_title_and_version(
    title: str,
    version: int,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_workflow_by_title_and_version(db, title, version)


@router.delete("/workflows/{title}/{version}", status_code=204)
async def delete_workflow(
    title: str,
    version: int,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.delete_workflow(db, title, version)


@router.get("/workflows/{title}/{version}/tasks", response_model=List[schemas.Task])
async def get_workflow_tasks(
    title: str,
    version: int,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_workflow_tasks(db, title, version)


@router.get(
    "/workflows/{title}/{version}/tasks/{task_title}", response_model=schemas.Task
)
async def get_task(
    title: str,
    version: int,
    task_title: str,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_task(db, title, version, task_title)
