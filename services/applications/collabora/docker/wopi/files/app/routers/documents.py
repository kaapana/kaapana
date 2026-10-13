from app.config import get_settings
from app.dependencies import (
    get_connection_manager,
    get_document_store,
    get_minio_client,
    get_wopi,
)
from app.model.documents import DocumentStore
from app.model.wopi import WOPI, editor_url
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(tags=["docs"])


@router.post("/refresh")
async def refresh_documents(
    doc_store: DocumentStore = Depends(get_document_store),
    wopi_srv=Depends(get_wopi),
    con_mgr=Depends(get_connection_manager),
    minio=Depends(get_minio_client),
):
    doc_store.find_documents(
        minio,
        wopi_srv.supported_extensions(),
        get_settings().document_path_ignore_regex,
    )
    await con_mgr.announce_documents()


@router.get("/")
async def read_documents(
    doc_store: DocumentStore = Depends(get_document_store),
    wopi_srv: WOPI = Depends(get_wopi),
):
    if not wopi_srv.apps:
        raise HTTPException(503, "Collabora is not available yet, no document editor was discovered")

    result = []
    for doc in doc_store.docs:
        match = wopi_srv.match(doc.extension)
        if match is None:
            continue
        file_id = doc_store.get_file_id(doc.path)
        result.append(
            {
                "file_id": file_id,
                "file": doc,
                "favicon": match.app.favicon,
                "app_name": match.app.name,
                "action_name": match.action.name,
                "url": editor_url(match.action.url, f"{get_settings().wopi_api_endpoint}/wopi/files/{file_id}"),
            }
        )
    return result
