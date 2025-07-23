from app import models, schemas, crud
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from sqlalchemy import select, update
from app.schemas import LifecycleStatus
from datetime import datetime
from typing import Dict, Any
import app.services.celery as celery

    
async def create_workflow_run(db: AsyncSession, forwarded_headers: Dict[str, str], workflow_run: schemas.WorkflowRunCreate, 
                            workflow_id: int) -> models.WorkflowRun:
    """Create workflow run and submit via Celery"""
    db_workflow_run = await crud.create_workflow_run(db, workflow_run=workflow_run, workflow_id=workflow_id)
    # Submit to Celery for background processing
    task = celery.trigger_workflow_run.delay(
        forwarded_headers=forwarded_headers,
        workflow_run_id=db_workflow_run.id,
        workflow_identifier=db_workflow_run.workflow.identifier,
        config=workflow_run.config,
        labels=workflow_run.labels
    )
    # Store Celery task ID for tracking
    await db.execute(
        update(models.WorkflowRun)
        .where(models.WorkflowRun.id == db_workflow_run.id)
        .values(celery_task_id=task.id)
    )
    await db.commit()
    
    print(f"Created workflow run {db_workflow_run.id} with Celery task {task.id}")
    return db_workflow_run

async def get_workflow_run_status(db: AsyncSession, workflow_run_id: int) -> Dict[str, Any]:
    """Get workflow run status including Celery task info"""

    result = await db.execute(
        select(models.WorkflowRun).where(
            models.WorkflowRun.id == workflow_run_id
        )
    )
    workflow_run = result.scalar_one_or_none()
    
    if not workflow_run:
        return None
    
    response = {
        'workflow_run_id': workflow_run_id,
        'lifecycle_status': workflow_run.lifecycle_status.value,
        'external_id': workflow_run.external_id,
        'updated_at': workflow_run.updated_at.isoformat() if workflow_run.updated_at else None
    }
    
    # Get Celery task status if available
    if workflow_run.celery_task_id:
        task_result = AsyncResult(workflow_run.celery_task_id, app=celery_app)
        response['celery_task_status'] = task_result.state
        response['celery_task_id'] = workflow_run.celery_task_id
    
    return response

async def cancel_workflow_run(db: AsyncSession, workflow_run_id: int) -> bool:
    """Cancel workflow run"""
    result = await db.execute(
        select(models.WorkflowRun).where(
            models.WorkflowRun.id == workflow_run_id
        )
    )
    workflow_run = result.scalar_one_or_none()
    
    if not workflow_run:
        return False
    
    # Cancel Celery task if it exists
    if workflow_run.celery_task_id:
        celery_app.control.revoke(workflow_run.celery_task_id, terminate=True)
    
    # Submit cancellation task if we have external ID
    if workflow_run.external_id:
        cancel_workflow_task.delay(workflow_run_id, workflow_run.external_id)
    else:
        # No external ID, just update database
        await db.execute(
            update(models.WorkflowRun)
            .where(models.WorkflowRun.id == workflow_run_id)
            .values(
                lifecycle_status=LifecycleStatus.CANCELED,
                updated_at=datetime.now()
            )
        )
        await db.commit()
    
    return True

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