import http
from httpcore import request
from fastapi import (
    APIRouter,
    UploadFile,
    Response,
    File,
    Header,
    Depends,
    HTTPException,
)
import requests
from app.workflows import utils
from app.dependencies import get_db, Session, get_workflow_service
from .services import WorkflowService

router = APIRouter(tags=["workflows"])


@router.get("/all")
async def dags(service: WorkflowService = Depends(get_workflow_service)):
    resp, err = service.get_dags()
    if err:
        return {
            "get_dags failed with Status Code: {0} , Error: {1}".format(
                err.detail, err.status_code
            )
        }
    return resp


@router.post("/trigger")
async def trigger_workflow(
    conf_data: dict,
    dry_run: str = True,
    db: Session = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
):
    db_client_kaapana = crud.get_kaapana_instance(db)
    resp, err = service.trigger_workflow(db_client_kaapana, conf_data, dry_run)
    if err:
        raise HTTPException(
            "trigger_workflow failed with Status Code: {0} , Error: {1} , ".format(
                err.detail, err.status_code
            )
        )
    return resp


@router.get("/running")
async def running_dags(service: WorkflowService = Depends(get_workflow_service)):
    ###### returns [dag_id] for currently running DAGs ######
    resp, err = service.get_running_dags()
    if err:
        raise HTTPException(
            "get_running_dags failed with Status Code: {0} , Error: {1}".format(
                err.detail, err.status_code
            )
        )
    return resp


@router.get("/history/{dag_id}")
async def dag_history(
    dag_id: str, service: WorkflowService = Depends(get_workflow_service)
):
    ###### returns [dag_id] for currently running DAGs ######
    resp, err = service.get_dag_history(dag_id)
    if err:
        raise HTTPException(
            detail="get_dag_history failed {0}".format(err.detail),
            status_code=err.status_code,
        )
    return resp
