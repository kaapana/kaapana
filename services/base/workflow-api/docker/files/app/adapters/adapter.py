from app import models, schemas, crud
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.schemas import LifecycleStatus
from datetime import datetime
from typing import Dict, Any
import app.adapters.celery as celery

    
async def create_workflow_run(db: AsyncSession, forwarded_headers: Dict[str, str], project: Dict[str, Any] , workflow_run: schemas.WorkflowRunCreate, 
                            workflow_id: int) -> models.WorkflowRun:
    """Create workflow run and submit via Celery"""
    
    # add project to config
    if project:
        workflow_run.config['project_form'] = project

    db_workflow_run = await crud.create_workflow_run(db, workflow_run=workflow_run, workflow_id=workflow_id)


    # Submit to Celery for background processing
    celery_task = celery.submit_workflow_run.delay(
        forwarded_headers=forwarded_headers,
        workflow_id=workflow_id,
        workflow_run_id=db_workflow_run.id,
        workflow_identifier=db_workflow_run.workflow.identifier,
        config=workflow_run.config,
        labels=workflow_run.labels
    )
    # Store Celery task ID for tracking
    await db.execute(
        update(models.WorkflowRun)
        .where(models.WorkflowRun.id == db_workflow_run.id)
        .values(celery_task_id=celery_task.id)
    )
    await db.commit()
    
    print(f"Created workflow run {db_workflow_run.id} with Celery task {celery_task.id}")
    # get update workflow run with task runs
    db_workflow_run = await crud.get_workflow_runs(
        db,
        filters={"id": db_workflow_run.id},
        single=True,
    )
    return db_workflow_run

# TODO remove this function when AirflowAdapter is fully implemented
def test_airflow_connection(forwarded_headers: Dict[str, str]) -> bool:
    logging.warning(f"Testing Airflow connection with forwarded headers: {forwarded_headers}")
    adapter = celery.get_adapter_for_workflow(workflow_type="airflow", forwarded_headers=forwarded_headers)
    adapter.base_url = "http://airflow-webserver-service.services.svc:8080/flow"
    logging.warning(f"Testing Airflow connection with extra_headers: {adapter.extra_headers}")
    endpoint = f"/api/v1/dags"
    value = adapter._request("GET", endpoint)
    logging.warning(f"Airflow health check response: {value}")
    return True

async def cancel_workflow_run(db: AsyncSession, forwarded_headers: Dict[str, str], workflow_run_id: int) -> bool:
    """Cancel workflow run"""
    result = await db.execute(
        select(models.WorkflowRun).where(
            models.WorkflowRun.id == workflow_run_id)
            .options(selectinload(models.WorkflowRun.workflow))
    )
    workflow_run = result.scalar_one_or_none()
    
    if not workflow_run:
        return False
    
    workflow_identifier = workflow_run.workflow.identifier
        
    # Submit cancellation task if we have external ID
    if workflow_run.external_id and workflow_run.lifecycle_status not in [LifecycleStatus.CANCELED, LifecycleStatus.COMPLETED]:
        celery.cancel_workflow.delay(forwarded_headers=forwarded_headers, workflow_run_id=workflow_run_id, workflow_identifier=workflow_identifier, external_id=workflow_run.external_id)
    else:
        return False
   
    return True

#TODO not tested/implemented correct
async def get_workflow_run_logs(db: AsyncSession, workflow_run_id: int) -> Dict[str, Any]:
    """Get workflow run logs including Celery task logs"""
    result = await db.execute(
        select(models.WorkflowRun).where(
            models.WorkflowRun.id == workflow_run_id
        )
    )
    workflow_run = result.scalar_one_or_none()
    
    if not workflow_run or not workflow_run.celery_task_id:
        return {'logs': []}
    
    # Get task result and info
    task_result = AsyncResult(workflow_run.celery_task_id, app=celery_app)
    
    return {
        'workflow_run_id': workflow_run_id,
        'celery_task_id': workflow_run.celery_task_id,
        'task_state': task_result.state,
        'task_result': task_result.result if task_result.ready() else None,
        'task_traceback': task_result.traceback if task_result.failed() else None
    }