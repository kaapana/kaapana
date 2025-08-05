from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
import json
from app.dependencies import get_async_db, get_project, get_project_id, get_forwarded_headers
from app.services import service as workflow_service
from app import crud, schemas
from typing import Dict, Any
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
@router.get("/", response_model=List[schemas.Workflow])
async def get_workflows(project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    workflows = await crud.get_workflows(db, project_id=project_id)
    return workflows

@router.post("/", response_model=schemas.Workflow)
async def create_workflow(workflow: schemas.WorkflowCreate, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    db_workflow = await crud.create_workflow(db, project_id=project_id, workflow=workflow)
    return db_workflow

@router.get("/tasks/{task_id}", response_model=schemas.Task)
async def get_tasks(task_id: int, db: AsyncSession = Depends(get_async_db)):
    db_task = await crud.get_tasks(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found!")
    return db_task


@router.get("/{identifier}/latest", response_model=schemas.Workflow)
async def get_latest_version_workflow(identifier: str, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    db_workflow = await crud.get_latest_workflow_by_identifier(db, identifier=identifier, project_id=project_id)
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return db_workflow


@router.get("/{identifier}/versions", response_model=List[schemas.Workflow])
async def get_workflow_versions(identifier: str, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    db_workflows = await crud.get_workflow_versions(db, project_id=project_id, identifier=identifier)
    if not db_workflows:
        raise HTTPException(status_code=404, detail="No versions found for this workflow identifier")
    return db_workflows


@router.get("/{identifier}/{version}", response_model=schemas.Workflow)
async def get_workflow_by_identifier_and_version(identifier: str, version: int, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    db_workflow = await crud.get_workflow_by_identifier_and_version(db, identifier=identifier, version=version, project_id=project_id)
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return db_workflow


@router.delete("/{identifier}/{version}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(identifier: str,version: int, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):    
    success = await crud.delete_workflow(db, identifier=identifier, version=version, project_id=project_id)
    # TODO: Also delete related UI schema, if exists
    # and related tasks, but not task-runs? But then task-runs would be orphaned?? So maybe not delete tasks?
    # but for sure a delte task endpoint should be implemented
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return



@router.get("/{identifier}/{version}/tasks", response_model=List[schemas.Task])
async def get_workflow_tasks(identifier: str, version: int, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    db_workflow = await crud.get_workflow_by_identifier_and_version(db, project_id=project_id, identifier=identifier, version=version)
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found, cannot get tasks")
    tasks = await crud.get_tasks_by_workflow(db, workflow_id=db_workflow.id)
    return tasks




@router.post("/{identifier}/{version}/tasks", response_model=schemas.Task)
async def create_workflow_task(identifier: str, version: int, task_create: schemas.TaskCreate, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    db_workflow = await crud.get_workflow_by_identifier_and_version(db, project_id=project_id, identifier=identifier, version=version)
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found, cannot create task")
    db_task = await crud.create_task(db, workflow_id=db_workflow.id, task=task_create)
    return db_task




@router.post("/{identifier}/{version}/runs", response_model=schemas.WorkflowRun)
async def create_workflow_run(
    identifier: str,
    version: int,
    workflow_run_create: schemas.WorkflowRunCreate,
    forwarded_headers: Dict[str, str] =  Depends(get_forwarded_headers),
    project: Dict[str, Any] = Depends(get_project),
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):
    db_workflow = await crud.get_workflow_by_identifier_and_version(db, project_id=project_id, identifier=identifier, version=version)
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db_workflow_run = await workflow_service.create_workflow_run(db, forwarded_headers=forwarded_headers, project=project, workflow_run=workflow_run_create, workflow_id=db_workflow.id)
    
    # Here you would interact with your Workflow Engine to schedule the run
    return db_workflow_run



# Workflow Run Endpoints
@router.get("/runs", response_model=List[schemas.WorkflowRun])
async def get_runs(dataset: Optional[str] = None ,limit: Optional[int] = None, labels: Optional[str] = None, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    runs = await crud.get_workflow_runs(db, project_id=project_id, limit=limit, labels=labels, dataset=dataset)
    return runs

@router.get("/{identifier}/runs/", response_model=List[schemas.WorkflowRun])
async def get_run_by_workflow_identifier(identifier: str, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    print("db_workflow")
    db_workflow = await crud.get_latest_workflow_by_identifier(db, project_id=project_id, identifier=identifier)
    print(db_workflow)
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    # Assuming you want the latest run for this workflow
    runs = await crud.get_workflow_runs_by_workflow(db, workflow_id=db_workflow.id)
    if not runs:
        raise HTTPException(status_code=404, detail="No runs found for this workflow")
    return runs

@router.get("/{identifier}/{version}/runs/{run_id}", response_model=schemas.WorkflowRun)
async def get_workflow_run(identifier: str, version: int, run_id: int, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    db_workflow_run = await crud.get_workflow_run(db, workflow_run_id=run_id)
    if db_workflow_run is None:
        raise HTTPException(status_code=404, detail="Workflow Run not found for this workflow")
    return db_workflow_run

@router.get("/runs/{run_id}/task-runs", response_model=List[schemas.TaskRun])
async def get_workflow_run_task_runs(run_id: int, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    task_runs = await crud.get_task_runs_by_workflow_run(db, workflow_run_id=run_id)
    return task_runs


@router.get("/{identifier}/{version}/runs/{run_id}/task/{task_id}/run", response_model=schemas.TaskRun)
async def get_task_run(identifier: str, version: int, run_id: int, task_id: int, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    db_workflow_run = await crud.get_workflow_run(db, workflow_run_id=run_id)
    if db_workflow_run is None:
        raise HTTPException(status_code=404, detail="Workflow Run not found for this workflow")
    db_task_run = await crud.get_task_run_by_task_and_workflow_run(db, task_id=task_id, workflow_run_id=run_id)
    if db_task_run is None:
        raise HTTPException(status_code=404, detail="Task Run not found for this workflow run and task")
    return db_task_run

@router.get("/{identifier}/{version}/runs/{run_id}/task/{task_id}/run/logs")
async def get_task_run_logs(identifier: str, version: int, run_id: int, task_id: int, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    db_workflow_run = await crud.get_workflow_run(db, workflow_run_id=run_id)
    if db_workflow_run is None:
        raise HTTPException(status_code=404, detail="Workflow Run not found for this workflow")
    db_task_run = await crud.get_task_run_by_task_and_workflow_run(db, task_id=task_id, workflow_run_id=run_id)
    if db_task_run is None:
        raise HTTPException(status_code=404, detail="Task Run not found for this workflow run and task")

    # Placeholder for fetching logs from workflow engine
    logs = f"Logs for Task ID {task_id} in Run ID {run_id}"
    return {"logs": logs}

@router.put("/runs/{run_id}/cancel", response_model=bool)
async def cancel_workflow_run(run_id: int, db: AsyncSession = Depends(get_async_db), forwarded_headers: Dict[str, str] =  Depends(get_forwarded_headers)):
    success = await workflow_service.cancel_workflow_run(db, forwarded_headers, workflow_run_id=run_id)
    # Here you would interact with your Workflow Engine to signal cancellation
    return success


## Workflow UI Schema Endpoints



@router.get("/{identifier}/version/{version}/ui-schema", response_model=schemas.WorkflowUISchema)
async def get_workflow_ui_schema(identifier: str, version: int, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    db_ui_schema = await crud.get_workflow_ui_schema(db, identifier=identifier, version=version)
    if db_ui_schema is None:
        raise HTTPException(status_code=404, detail="Workflow UI Schema not found")
    return db_ui_schema



@router.get("/{identifier}/ui-schema", response_model=schemas.WorkflowUISchema)
async def get_latest_workflow_ui_schema_route(identifier: str, project_id=Depends(get_project_id), db: AsyncSession = Depends(get_async_db)):
    db_ui_schema = await crud.get_latest_workflow_ui_schema(db, identifier=identifier)
    if db_ui_schema is None:
        raise HTTPException(status_code=404, detail="Workflow UI Schema not found for the latest version")
    return db_ui_schema


@router.post("/{identifier}/versions/{version}/ui-schema", response_model=schemas.WorkflowUISchema)
async def create_workflow_ui_schema(
 identifier: str,
 version: int,
 ui_schema: schemas.WorkflowUISchemaCreate,
 project_id=Depends(get_project_id),
 db: AsyncSession = Depends(get_async_db)
):
    db_ui_schema = await crud.create_workflow_ui_schema(db, identifier=identifier, version=version, ui_schema=ui_schema)
    return db_ui_schema


@router.post("/{identifier}/versions/latest/ui-schema", response_model=schemas.WorkflowUISchema)
async def create_workflow_ui_schema_latest(
 identifier: str,
 ui_schema_create: schemas.WorkflowUISchemaCreate,
 project_id=Depends(get_project_id),
 db: AsyncSession = Depends(get_async_db)
):
    # This endpoint creates a UI schema for the *latest* workflow version.
    # The logic to get the latest version and create the schema is handled in crud.
    db_ui_schema = await crud.create_workflow_ui_schema_for_latest_version(db, identifier=identifier, ui_schema_create=ui_schema_create)
    return db_ui_schema



from celery import Celery
from celery.result import AsyncResult
from app.config import celery_app

# Celery monitoring endpoints
@router.get("/celery/status")
async def get_celery_status():
    """Get Celery cluster status"""
    inspect = celery_app.control.inspect()
    return {
        'active_tasks': inspect.active(),
        'scheduled_tasks': inspect.scheduled(),
        'stats': inspect.stats()
    }

@router.get("/celery/tasks/{task_id}")
async def get_celery_task_status(task_id: str):
    """Get specific Celery task status"""
    task_result = AsyncResult(task_id, app=celery_app)
    return {
        'task_id': task_id,
        'state': task_result.state,
        'result': task_result.result if task_result.ready() else None,
        'traceback': task_result.traceback if task_result.failed() else None
    }

@router.get("/test-airflow")
async def test_airflow_connection(forwarded_headers: Dict[str, str] =  Depends(get_forwarded_headers)):
    test = workflow_service.test_airflow_connection(forwarded_headers=forwarded_headers)
    if not test:
        raise HTTPException(status_code=500, detail="Failed to connect to Airflow")