import datetime

from app.dependencies import get_connection_manager, get_minio_client, get_username
from app.model.documents import decode_file_id, open_document, stat_document, write_document
from app.model.websockets import ConnectionManager
from fastapi import APIRouter, Depends, Header, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

# WOPI REST API Reference
# https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/
router = APIRouter(tags=["wopi"])

DOCUMENT_MODIFIED_STATUS = 1010
CHUNK_SIZE = 64 * 1024


def wopi_timestamp(value: datetime.datetime) -> str:
    return value.astimezone(datetime.timezone.utc).isoformat()


@router.get("/files/{file_id}")
def check_file_info(
    file_id: str,
    minio=Depends(get_minio_client),
    username=Depends(get_username),
):
    bucket, path = decode_file_id(file_id)
    doc = stat_document(minio, bucket, path)
    return {
        "BaseFileName": path.split("/")[-1],  # Only the accutal filename instead of the filepath
        "OwnerId": bucket,
        "Size": doc.size,
        "UserId": username or "anonymous",
        "UserFriendlyName": username or "Unknown user",
        "Version": doc.version,
        "LastModifiedTime": wopi_timestamp(doc.modification_time),
        "UserCanWrite": True,
        "UserCanNotWriteRelative": True,
        "SupportsUpdate": True,
    }


@router.get("/files/{file_id}/contents")
def get_file(file_id: str, minio=Depends(get_minio_client)):
    bucket, path = decode_file_id(file_id)
    response = open_document(minio, bucket, path)

    def release():
        response.close()
        response.release_conn()

    return StreamingResponse(
        response.stream(CHUNK_SIZE),
        media_type="application/octet-stream",
        headers={"X-WOPI-ItemVersion": response.headers.get("ETag", "").strip('"')},
        background=BackgroundTask(release),
    )


@router.post("/files/{file_id}/contents")
async def put_file(
    file_id: str,
    request: Request,
    minio=Depends(get_minio_client),
    con_mgr: ConnectionManager = Depends(get_connection_manager),
    timestamp: str | None = Header(None, alias="X-COOL-WOPI-Timestamp"),
):
    bucket, path = decode_file_id(file_id)
    if timestamp:
        current = await run_in_threadpool(stat_document, minio, bucket, path)
        if wopi_timestamp(current.modification_time) != timestamp:
            return JSONResponse({"COOLStatusCode": DOCUMENT_MODIFIED_STATUS}, status_code=409)

    body = await request.body()
    doc = await run_in_threadpool(write_document, minio, bucket, path, body)
    await con_mgr.announce_documents(bucket)
    return JSONResponse(
        {"LastModifiedTime": wopi_timestamp(doc.modification_time)},
        headers={"X-WOPI-ItemVersion": doc.version or ""},
    )
