import asyncio
from app import crud
from app.database import async_session
from app import schemas
from app.adapters import get_workflow_engine


async def update_by_lifecycle(db, status: schemas.LifecycleStatus):
    workflow_runs = await crud.get_workflow_runs(
        db=db, filters={"lifecycle_status": status}
    )

    for wf_run in workflow_runs:
        workflow = await crud.get_workflows(
            db,
            filters={
                "title": wf_run.workflow.title,
                "version": wf_run.workflow.version,
            },
            single=True,
        )
        engine = get_workflow_engine(workflow)
        workflow_run_update = engine.get_workflow_run(wf_run)
        await crud.update_workflow_run(
            db, run_id=wf_run.id, workflow_run_update=workflow_run_update
        )


async def main():
    async with async_session() as db:
        await update_by_lifecycle(db, status=schemas.LifecycleStatus.SCHEDULED)
        await update_by_lifecycle(db, status=schemas.LifecycleStatus.PENDING)
        await update_by_lifecycle(db, status=schemas.LifecycleStatus.RUNNING)


if __name__ == "__main__":
    asyncio.run(main())
