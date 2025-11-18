import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, BinaryIO, List

import aiohttp
import httpx
import requests
from app.config import settings
from app.dependencies import get_db
from app.workflows import crud, schemas
from app.workflows.utils import requests_retry_session
from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Response,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse
from urllib3.util import Timeout

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


async def stream_upload_to_minio(
    file_data: BinaryIO, presigned_url: str, settings, filename: str = "unknown"
) -> AsyncGenerator[str, None]:
    """Stream MinIO response without buffering"""
    upload_id = f"{datetime.now().isoformat()}-{filename}"

    try:
        logging.info(f"[{upload_id}] Starting upload")
        yield f"[{upload_id}] Uploading...\n"

        def upload_sync():
            with requests.Session() as s:
                return requests_retry_session(session=s).put(
                    f"http://minio-service.{settings.services_namespace}.svc:9000{presigned_url}",
                    data=file_data,
                    stream=True,
                )

        response = await run_in_threadpool(upload_sync)

        # DON'T wait for full response - stream chunks immediately
        yield f"[{upload_id}] Status: {response.status_code}\n"

        # Stream MinIO response chunks WITHOUT buffering
        chunk_count = 0
        for chunk in response.iter_content(chunk_size=1024):  # Small chunks!
            if chunk:
                chunk_count += 1
                # Yield immediately, don't buffer
                yield chunk.decode("utf-8", errors="ignore")

        yield f"\n[{upload_id}] Complete\n"
        logging.info(f"[{upload_id}] SUCCESS")

    except Exception as e:
        logging.error(f"[{upload_id}] Error: {str(e)}", exc_info=True)
        yield f"\n[{upload_id}] ERROR: {str(e)}\n"


@router.post("/minio-presigned-url")
async def post_minio_presigned_url(
    file: UploadFile = File(...),
    presigned_url: str = Header(...),
):
    logging.info(f"Upload: {file.filename}")

    try:
        file_copy = UploadFile(
            file=file.file,
            size=file.size,
            filename=file.filename,
            headers=file.headers,
        )
        file.file = BinaryIO()
        file_copy.file.seek(0)

        return StreamingResponse(
            stream_upload_to_minio(
                file_copy.file, presigned_url, settings, file.filename
            ),
            media_type="text/event-stream",
            status_code=200,
        )

    except Exception as e:
        logging.error(f"Error: {str(e)}", exc_info=True)
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=500,
        )


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
    job = crud.update_job(db, job, remote=True)
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
