from app.dependencies import get_connection_manager, get_minio_client
from app.model.documents import decode_file_id, read_document, stat_document, write_document
from app.model.websockets import ConnectionManager
from fastapi import APIRouter, Body, Depends, Header
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse

# WOPI REST API Reference
# https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/
router = APIRouter(tags=["wopi"])


@router.get("/files/{file_id}/contents")
def read_file_conent(file_id: str, minio=Depends(get_minio_client)):
    bucket, path = decode_file_id(file_id)
    return PlainTextResponse(read_document(minio, bucket, path))


@router.post("/files/{file_id}/contents")
async def store_file_meta(
    file_id: str,
    body=Body(...),
    content_type: str = Header(...),
    minio=Depends(get_minio_client),
    con_mgr: ConnectionManager = Depends(get_connection_manager),
):
    bucket, path = decode_file_id(file_id)
    await run_in_threadpool(write_document, minio, bucket, path, body)
    await con_mgr.announce_documents(bucket)


@router.get("/files/{file_id}")
def read_file_meta(file_id: str, minio=Depends(get_minio_client)):
    bucket, path = decode_file_id(file_id)
    doc = stat_document(minio, bucket, path)
    return {
        "BaseFileName": path.split("/")[-1],  # Only the accutal filename instead of the filepath
        "Size": doc.size,
        "UserCanWrite": True,
    }
