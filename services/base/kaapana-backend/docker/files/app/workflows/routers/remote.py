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
import aiohttp
from starlette.responses import StreamingResponse

logging.getLogger().setLevel(logging.INFO)

TIMEOUT_SEC = 5
TIMEOUT = Timeout(TIMEOUT_SEC)

router = APIRouter(tags=["remote"])


@router.get("/minio-presigned-url")
async def get_minio_presigned_url(presigned_url: str = Header(...)):
    logging.debug(
        f"http://minio-service.{settings.services_namespace}.svc:9000{presigned_url}"
    )

    # file streaming to get large files from minio
    async def stream_minio_response():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://minio-service.{settings.services_namespace}.svc:9000{presigned_url}"
                ) as resp:
                    resp.raise_for_status()
                    while True:
                        chunk = await resp.content.read(
                            8192
                        )  # Adjust chunk size as needed
                        if not chunk:
                            break
                        yield chunk
        except aiohttp.ClientError as e:
            logging.error(f"Error fetching from MinIO: {e}")
            raise HTTPException(status_code=500, detail="Error fetching from MinIO")

    return StreamingResponse(stream_minio_response(), status_code=200)


@router.post("/minio-presigned-url")
async def post_minio_presigned_url(
    file: UploadFile = File(...), presigned_url: str = Header(...)
):
    # Todo add file streaming!
    with requests.Session() as s:
        resp = requests_retry_session(session=s).put(
            f"http://minio-service.{settings.services_namespace}.svc:9000{presigned_url}",
            data=file.file,
        )
    return Response(resp.content, resp.status_code)


# deprecated should be removed, if unused
@router.get("/job", response_model=schemas.JobWithKaapanaInstance)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = crud.get_job(db, job_id)
    job.kaapana_instance = schemas.KaapanaInstance.clean_full_return(
        job.kaapana_instance
    )
    return job


# deprecated should be removed, if unused
@router.get("/jobs", response_model=List[schemas.JobWithKaapanaInstance])
def get_jobs(
    instance_name: str = None,
    status: str = None,
    limit: int = None,
    db: Session = Depends(get_db),
):
    jobs = crud.get_jobs(db, instance_name, status, remote=True, limit=limit)
    for job in jobs:
        if job.kaapana_instance:
            job.kaapana_instance = schemas.KaapanaInstance.clean_full_return(
                job.kaapana_instance
            )
    return jobs


# response_model should only return what is nessary (e.g. probably only success)
@router.put("/job", response_model=schemas.JobWithKaapanaInstance)
def put_job(job: schemas.JobUpdate, db: Session = Depends(get_db)):
    job = crud.bulk_update_jobs(db, [job], remote=True)
    if job.kaapana_instance:
        job.kaapana_instance = schemas.KaapanaInstance.clean_full_return(
            job.kaapana_instance
        )
    return job


# deprecated should be removed, if unused
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


@router.put("/workflow", response_model=schemas.Workflow)
def put_workflow(workflow: schemas.WorkflowUpdate, db: Session = Depends(get_db)):
    return crud.update_workflow(db, workflow)
