from app.config import settings, celery_app
from app.adapters.airflow_adapter import AirflowAdapter
from app.models import LifecycleStatus
from sqlalchemy import select, update
from datetime import datetime
from typing import Dict, Any
from celery.exceptions import MaxRetriesExceededError
from app.database import sync_session
from app import models
#from app.dependencies import get_adapter_for_workflow

MONITOR_INTERVAL = 30  # Check again in 30 seconds
def get_adapter_for_workflow(workflow_type: str, forwarded_headers: dict) -> 'WorkflowEngineAdapter':
    """
    Factory function to get the appropriate workflow engine adapter based on the workflow type.
    Args:
        workflow_type (str): The type of workflow engine (e.g. "airflow").
        forwarded_headers (dict): Headers to pass to the adapter, e.g. access tokens.
    Returns:
        WorkflowEngineAdapter: An instance of the appropriate adapter.
    Raises:
        ValueError: If the workflow type is not recognized.
    """
    if not workflow_type:
        raise ValueError("Workflow type must be specified")

    if workflow_type == "airflow":
        return AirflowAdapter(settings.AIRFLOW_URL, extra_headers=forwarded_headers)
    else:
        raise ValueError(f"Unknown workflow engine: {workflow_type}")

# Celery Tasks
@celery_app.task(bind=True, name='trigger_workflow_run')
def trigger_workflow_run(self, forwarded_headers: Dict[str, str], workflow_run_id: int, workflow_identifier: str, config: Dict[str, Any],
                         labels: Dict[str, str] = None):
    """
    Celery task to submit a workflow to an external engine (e.g. Airflow) and update its status.
    If successful, it schedules a monitoring task.
    """
    #TODO
    workflow_type = "airflow"  # This should be determined based on the workflow-label or other context
    # Initialize the Airflow adapter with the base URL and access token
    adapter: WorkflowEngineAdapter = get_adapter_for_workflow(
        workflow_type, forwarded_headers
    )

    try:
        # Submit the workflow to the external engine
        print(f"Submitting workflow run {workflow_run_id} to Airflow with config: {config}")
        result = adapter.trigger_workflow_run(workflow_run_id, workflow_identifier, config, labels)
        print(f"Workflow run {workflow_run_id} submitted successfully: {result}")

        # Update the database with the external ID and initial status from the submission result
        with sync_session() as db:
            db.execute(
                update(models.WorkflowRun)
                .where(models.WorkflowRun.id == workflow_run_id)
                .values(
                    external_id=result.external_id,
                    lifecycle_status=result.status,
                    updated_at=datetime.now()
                )
            )
            db.commit()

        # If an external ID is returned, schedule the monitoring task
        if result.external_id:
            # Pass only serializable arguments to the next task
            monitor_workflow_task.delay(workflow_run_id, workflow_identifier, result.external_id)

        return {
            'workflow_run_id': workflow_run_id,
            'external_id': result.external_id,
            'status': result.status.value,
            'success': True
        }

    except Exception as e:
        # If submission fails, update the workflow run status to ERROR in the database
        with sync_session() as db:
            db.execute(
                update(models.WorkflowRun)
                .where(models.WorkflowRun.id == workflow_run_id)
                .values(
                    lifecycle_status=LifecycleStatus.ERROR,
                    updated_at=datetime.now()
                )
            )
            db.commit()

        # Re-raise the exception for Celery to handle, with retry logic
        # Retries up to 3 times with a 60-second countdown between attempts
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, name='monitor_workflow')
def monitor_workflow_task(self, workflow_run_id: int, workflow_identifier: str, external_id: str):
    """
    Celery task to monitor the status of a workflow run in the external engine.
    It updates the database and reschedules itself if the workflow is not in a final state.
    """
    # Initialize the Airflow adapter.
    adapter = AirflowAdapter(settings.AIRFLOW_URL)

    try:
        # Get the current status of the workflow run from the database
        with sync_session() as db:
            workflow_run = db.execute(
                select(models.WorkflowRun).where(
                    models.WorkflowRun.id == workflow_run_id
                )
            ).scalar_one_or_none()

            if not workflow_run:
                print(f"Workflow run {workflow_run_id} not found in DB, stopping monitoring.")
                return {'status': 'not_found', 'final': True}

            current_status = workflow_run.lifecycle_status

            # If the workflow is already in a final state in the DB, stop monitoring
            if current_status in [LifecycleStatus.COMPLETED,
                                  LifecycleStatus.ERROR,
                                  LifecycleStatus.CANCELED]:
                print(f"Workflow run {workflow_run_id} is already in a final state ({current_status.value}), stopping monitoring.")
                return {'status': current_status.value, 'final': True}

            # Get the latest status from the external engine
            external_status = adapter.get_workflow_run_status(workflow_identifier, external_id)
            print(f"Workflow run {workflow_run_id} (external ID: {external_id}) - DB status: {current_status.value}, External status: {external_status.value}")

            # Update the database if the status has changed
            if external_status != current_status:
                db.execute(
                    update(models.WorkflowRun)
                    .where(models.WorkflowRun.id == workflow_run_id)
                    .values(
                        lifecycle_status=external_status,
                        updated_at=datetime.now()
                    )
                )
                db.commit()
                print(f"Workflow run {workflow_run_id} status updated to {external_status.value}.")

            # Check if the external status indicates a final state
            if external_status in [LifecycleStatus.COMPLETED,
                                   LifecycleStatus.ERROR,
                                   LifecycleStatus.CANCELED]:
                print(f"Workflow run {workflow_run_id} reached final state ({external_status.value}), stopping monitoring.")
                return {'status': external_status.value, 'final': True}

            # If not in a final state, reschedule the monitoring task
            monitor_workflow_task.apply_async(
                args=[workflow_run_id, workflow_identifier, external_id],
                countdown=MONITOR_INTERVAL
            )
            print(f"Workflow run {workflow_run_id} monitoring rescheduled for {MONITOR_INTERVAL} seconds.")
            return {'status': external_status.value, 'final': False}
    except MaxRetriesExceededError:
        print(f"Max retries exceeded for workflow run {workflow_run_id}")
    raise
    except Exception as e:
        # Retry with exponential backoff if an error occurs during monitoring
        # Retries up to 10 times with a 60-second countdown between attempts
        print(f"Error monitoring workflow run {workflow_run_id}: {e}. Retrying...")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, name='cancel_workflow_run')
def cancel_workflow_task(self, workflow_run_id: int, external_id: str):
    """
    Celery task to cancel a workflow run in the external engine.
    It updates the database status if the cancellation is successful.
    """
    # Initialize the Airflow adapter with the base URL
    adapter = AirflowAdapter(settings.AIRFLOW_URL)

    try:
        # Attempt to cancel the workflow in the external engine
        print(f"Attempting to cancel workflow run {workflow_run_id} with external ID: {external_id}")
        success = adapter.cancel_workflow_run(external_id)

        if success:
            # If cancellation is successful, update the database status to CANCELED
            with sync_session() as db:
                db.execute(
                    update(models.WorkflowRun)
                    .where(models.WorkflowRun.id == workflow_run_id)
                    .values(
                        lifecycle_status=LifecycleStatus.CANCELED,
                        updated_at=datetime.now()
                    )
                )
                db.commit()
            print(f"Workflow run {workflow_run_id} successfully canceled and DB status updated.")
        else:
            print(f"Failed to cancel workflow run {workflow_run_id} in external engine.")

        return {'success': success}

    except Exception as e:
        # Retry with exponential backoff if an error occurs during cancellation
        # Retries up to 3 times with a 30-second countdown between attempts
        print(f"Error canceling workflow run {workflow_run_id}: {e}. Retrying...")
        raise self.retry(exc=e, countdown=30, max_retries=3)

