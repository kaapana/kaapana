from typing import List
import requests
import logging

from fastapi import (
    APIRouter,
    UploadFile,
    Response,
    File,
    Header,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session
from app.dependencies import get_db

from app.workflows import crud
from app.workflows import schemas
from app.workflows.utils import requests_retry_session
from app.config import settings
from urllib3.util import Timeout

logging.getLogger().setLevel(logging.INFO)

TIMEOUT_SEC = 5
TIMEOUT = Timeout(TIMEOUT_SEC)

router = APIRouter(tags=["remote"])


@router.get("/minio-presigned-url")
async def get_minio_presigned_url(presigned_url: str = Header(...)):
    logging.info(
        f"http://minio-service.{settings.services_namespace}.svc:9000{presigned_url}"
    )
    # # Todo add file streaming!
    with requests.Session() as s:
        resp = requests_retry_session(session=s).get(
            f"http://minio-service.{settings.services_namespace}.svc:9000{presigned_url}",
            timeout=TIMEOUT,
        )
    return Response(resp.content, resp.status_code)


@router.post("/minio-presigned-url")
async def post_minio_presigned_url(
    file: UploadFile = File(...), presigned_url: str = Header(...)
):
    # Todo add file streaming!
    with requests.Session() as s:
        resp = requests_retry_session(session=s).put(
            f"http://minio-service.{settings.services_namespace}.svc:9000{presigned_url}",
            data=file.file,
            timeout=TIMEOUT,
        )
    return Response(resp.content, resp.status_code)


@router.get("/job", response_model=schemas.JobWithKaapanaInstance)
def get_job(job_id: int, db: Session = Depends(get_db)):
    return crud.get_job(db, job_id)


@router.get("/jobs", response_model=List[schemas.JobWithKaapanaInstance])
def get_jobs(
    instance_name: str = None,
    status: str = None,
    limit: int = None,
    db: Session = Depends(get_db),
):
    return crud.get_jobs(db, instance_name, status, remote=True, limit=limit)


@router.put("/job", response_model=schemas.JobWithKaapanaInstance)
def put_job(job: schemas.JobUpdate, db: Session = Depends(get_db)):
    return crud.update_job(db, job, remote=True)


@router.delete("/job")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    return crud.delete_job(db, job_id, remote=True)


@router.put("/sync-client-remote")
def put_remote_kaapana_instance(
    remote_kaapana_instance: schemas.RemoteKaapanaInstanceUpdateExternal,
    instance_name: str = None,
    status: str = None,
    db: Session = Depends(get_db),
):
    return crud.sync_client_remote(
        db=db,
        remote_kaapana_instance=remote_kaapana_instance,
        instance_name=instance_name,
        status=status,
    )
