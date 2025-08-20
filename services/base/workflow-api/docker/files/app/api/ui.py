from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import (
    get_async_db,
    get_project_id,
)
from app import crud, schemas

router = APIRouter()


## Workflow UI Schema Endpoints
# TODO check if maybe only provide direct endpoints with workflow_id?
@router.get(
    "/workflows/{identifier}/versions/{version}/ui-schema",
    response_model=schemas.WorkflowUISchema,
)
async def get_workflow_ui_schema(
    identifier: str,
    version: int,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):
    workflow = await crud.get_workflows(
        db,
        filters={
            "identifier": identifier,
            "version": version,
            "project_id": project_id,
        },
        single=True,
    )
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    db_ui_schema = await crud.get_workflow_ui_schema(db, workflow_id=workflow.id)
    if db_ui_schema is None:
        raise HTTPException(status_code=404, detail="Workflow UI Schema not found")
    return db_ui_schema


@router.post(
    "/workflows/{identifier}/versions/{version}/ui-schema",
    response_model=schemas.WorkflowUISchema,
)
async def create_or_update_workflow_ui_schema(
    identifier: str,
    version: int,
    ui_schema: schemas.WorkflowUISchemaCreate,
    project_id=Depends(get_project_id),
    db: AsyncSession = Depends(get_async_db),
):
    workflow = await crud.get_workflows(
        db,
        filters={
            "identifier": identifier,
            "version": version,
            "project_id": project_id,
        },
        single=True,
    )
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db_ui_schema = await crud.create_or_update_workflow_ui_schema(
        db, ui_schema=ui_schema, workflow_id=workflow.id
    )
    return db_ui_schema
