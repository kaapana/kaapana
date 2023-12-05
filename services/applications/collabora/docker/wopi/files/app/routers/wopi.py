from fastapi import APIRouter, Body, Header, Depends
from app.dependencies import get_document_store
from app.model.documents import DocumentStore

# WOPI REST API Reference
# https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/
router = APIRouter(tags=["wopi"])


@router.get("/files/{file_id}/contents")
async def read_file_conent(
    file_id: str, doc_store: DocumentStore = Depends(get_document_store)
):
    return doc_store.get_document(file_id)


@router.post("/files/{file_id}/contents")
async def store_file_meta(
    file_id: str,
    body=Body(...),
    content_type: str = Header(...),
    doc_store: DocumentStore = Depends(get_document_store),
):
    return doc_store.write(file_id, body=body)


@router.get("/files/{file_id}")
async def read_file_meta(
    file_id: str, doc_store: DocumentStore = Depends(get_document_store)
):
    return {
        "BaseFileName": doc_store.filename(file_id),
        "Size": doc_store.size(file_id),
        "UserCanWrite": doc_store.writable(file_id),
    }
