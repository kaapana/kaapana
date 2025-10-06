import logging
from fastapi import APIRouter, Depends, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.dependencies import get_async_db
from app import schemas
from app.api.v1.services import workflow_service as service
from app.api.v1.routers import _map_service_exception

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/workflows", response_model=List[schemas.Workflow])
async def get_workflows(
    skip: int = 0,
    limit: int = 100,
    order_by: Optional[str] = None,
    order: Optional[str] = "desc",
    id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await service.get_workflows(db, skip, limit, order_by, order, id)
    except Exception as exc:
        _map_service_exception(exc)


@router.post("/workflows", response_model=schemas.Workflow, status_code=201)
async def create_workflow(
    workflow: schemas.WorkflowCreate,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        workflow_res = await service.create_workflow(db, workflow)
    except Exception as exc:
        _map_service_exception(exc)
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
    try:
        return await service.get_workflow_by_title(db, title, latest, order_by, order)
    except Exception as exc:
        _map_service_exception(exc)


@router.get("/workflows/{title}/{version}", response_model=schemas.Workflow)
async def get_workflow_by_title_and_version(
    title: str,
    version: int,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await service.get_workflow_by_title_and_version(db, title, version)
    except Exception as exc:
        _map_service_exception(exc)


@router.delete("/workflows/{title}/{version}", status_code=204)
async def delete_workflow(
    title: str,
    version: int,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        await service.delete_workflow(db, title, version)
    except Exception as exc:
        _map_service_exception(exc)


@router.get("/workflows/{title}/{version}/tasks", response_model=List[schemas.Task])
async def get_workflow_tasks(
    title: str,
    version: int,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await service.get_workflow_tasks(db, title, version)
    except Exception as exc:
        _map_service_exception(exc)


@router.get(
    "/workflows/{title}/{version}/tasks/{task_title}", response_model=schemas.Task
)
async def get_task(
    title: str,
    version: int,
    task_title: str,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await service.get_task(db, title, version, task_title)
    except Exception as exc:
        _map_service_exception(exc)
