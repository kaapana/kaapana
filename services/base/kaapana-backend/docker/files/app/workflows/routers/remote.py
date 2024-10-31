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
from fastapi import Request

logging.getLogger().setLevel(logging.INFO)

TIMEOUT_SEC = 5
TIMEOUT = Timeout(TIMEOUT_SEC)

router = APIRouter(tags=["remote"])


@router.get("/minio-presigned-url")
async def get_minio_presigned_url(
    request: Request,  # Include the request object to capture headers like Range
    presigned_url: str = Header(...),
):
    logging.info(
        f"http://minio-service.{settings.services_namespace}.svc:9000{presigned_url}"
    )

    # Forward client's Range header if present
    client_range_header = request.headers.get("Range")

    async def stream_minio_response():
        timeout = aiohttp.ClientTimeout(
            total=900,
            connect=None,
            sock_read=None,
        )
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {}
                if client_range_header:
                    logging.info(f"Client Range header: {client_range_header}")
                    headers["Range"] = client_range_header  # Forward the Range header

                async with session.get(
                    f"http://minio-service.{settings.services_namespace}.svc:9000{presigned_url}",
                    headers=headers,  # Pass the Range header to MinIO
                ) as resp:
                    # Log resp headers
                    logging.info(
                        f"Content-Length: {resp.headers.get('Content-Length')}"
                    )
                    logging.info(
                        "\n".join([f"{k}: {v}" for k, v in resp.headers.items()])
                    )

                    resp.raise_for_status()

                    # Stream content in chunks
                    while True:
                        chunk = await resp.content.read(
                            131072
                        )  # Adjust chunk size as needed
                        if not chunk:
                            break
                        yield chunk

        except aiohttp.ClientError as e:
            logging.error(f"Error fetching from MinIO: {e}")
            raise HTTPException(status_code=500, detail="Error fetching from MinIO")
        except Exception as e:
            logging.error(f"Error fetching from MinIO: {e}")
            raise HTTPException(status_code=500, detail="Error fetching from MinIO")

    # Fetch headers from MinIO response
    async with aiohttp.ClientSession() as session:
        headers = {}
        if client_range_header:
            headers["Range"] = client_range_header  # Forward the Range header to MinIO

        async with session.get(
            f"http://minio-service.{settings.services_namespace}.svc:9000{presigned_url}",
            headers=headers,
        ) as resp:
            # Determine if partial content or full content is being returned
            status_code = resp.status
            if status_code not in [200, 206]:  # Only handle full or partial content
                logging.error(f"Unexpected status code: {status_code}")
                raise HTTPException(
                    status_code=status_code, detail="Unexpected status from MinIO"
                )

            # Extract relevant headers to forward, including Content-Range if present
            headers_to_forward = {
                k: v
                for k, v in resp.headers.items()
                if k.lower()
                in [
                    "content-length",
                    "content-type",
                    "etag",
                    "last-modified",
                    "content-range",
                ]
            }

            # Forward the response with correct headers and status code
            return StreamingResponse(
                stream_minio_response(),
                status_code=status_code,
                headers=headers_to_forward,
            )


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


@router.put("/sync-client-remote")
def put_remote_kaapana_instance(
    client_to_remote_instance: schemas.RemoteKaapanaInstanceUpdateExternal,
    client_to_remote_jobs: List[schemas.JobUpdate],
    db: Session = Depends(get_db),
):
    return crud.sync_client_remote(
        db=db,
        client_to_remote_instance=client_to_remote_instance,
        client_to_remote_jobs=client_to_remote_jobs,
    )
