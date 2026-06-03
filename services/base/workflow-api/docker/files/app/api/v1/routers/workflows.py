import logging
import uuid
from typing import List, Optional

from app import schemas
from app.api.v1.services import workflow_service as service
from app.dependencies import get_async_db
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()

# workflows


@router.get("/workflows", response_model=List[schemas.Workflow])
async def get_workflows(
    skip: int = 0,
    limit: int = 100,
    order_by: Optional[str] = None,
    order: Optional[str] = "desc",
    id: Optional[uuid.UUID] = None,
    title: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_workflows(db, skip, limit, order_by, order, id, title)


@router.post("/workflows", response_model=schemas.Workflow, status_code=201)
async def create_workflow(
    workflow: schemas.WorkflowCreate,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
):
    workflow_res = await service.create_workflow(db, workflow)
    response.headers["Location"] = f"/workflows/{workflow_res.id}"
    return workflow_res


@router.get("/workflows/{workflow_id}", response_model=schemas.Workflow)
async def get_workflow_by_id(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_workflow_by_id(db, workflow_id)


@router.patch("/workflows/{workflow_id}", response_model=schemas.Workflow)
async def update_workflow(
    workflow_id: uuid.UUID,
    update: schemas.WorkflowUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.update_workflow(db, workflow_id, update)


@router.delete("/workflows/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
):
    await service.delete_workflow(db, workflow_id)


# revisions


@router.get(
    "/workflows/{workflow_id}/revisions",
    response_model=List[schemas.WorkflowRevision],
)
async def get_workflow_revisions(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_workflow_revisions(db, workflow_id)


# workflow revisions


@router.get(
    "/workflows/{workflow_id}/revisions/{increment}",
    response_model=schemas.WorkflowRevision,
)
async def get_workflow_revision(
    workflow_id: uuid.UUID,
    increment: int,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_workflow_revision(db, workflow_id, increment)


@router.post(
    "/workflows/{workflow_id}/revisions/{increment}/restore",
    response_model=schemas.Workflow,
)
async def restore_workflow_revision(
    workflow_id: uuid.UUID,
    increment: int,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.restore_workflow_revision(db, workflow_id, increment)


# tasks


@router.get("/workflows/{workflow_id}/tasks", response_model=List[schemas.Task])
async def get_workflow_tasks(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_workflow_tasks(db, workflow_id)


@router.get(
    "/workflows/{workflow_id}/tasks/{task_title}",
    response_model=schemas.Task,
)
async def get_task(
    workflow_id: uuid.UUID,
    task_title: str,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_task(db, workflow_id, task_title)


@router.get(
    "/workflows/{workflow_id}/revisions/{increment}/tasks",
    response_model=List[schemas.Task],
)
async def get_workflow_revision_tasks(
    workflow_id: uuid.UUID,
    increment: int,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_workflow_tasks(db, workflow_id, increment=increment)


@router.get(
    "/workflows/{workflow_id}/revisions/{increment}/tasks/{task_title}",
    response_model=schemas.Task,
)
async def get_revision_task(
    workflow_id: uuid.UUID,
    increment: int,
    task_title: str,
    db: AsyncSession = Depends(get_async_db),
):
    return await service.get_task(db, workflow_id, task_title, increment=increment)
