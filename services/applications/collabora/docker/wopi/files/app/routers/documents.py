from fastapi import APIRouter, Depends
from app.dependencies import (
    get_document_store,
    get_connection_manager,
    get_wopi,
    get_minio_client,
)
from app.model.wopi import WOPI
from app.model.documents import DocumentStore
from app.config import get_settings

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
    wopi_srv=Depends(get_wopi),
):
    result = []
    for doc in doc_store.docs:
        # log.debug("Found document %s, with extension %s", doc.path, doc.extension)

        apps = list(wopi_srv.get_apps_actions_for_files(doc.extension))

        # TODO allow multiple applications per file
        file_id = doc_store.get_file_id(doc.path)
        result.append(
            {
                "file_id": file_id,
                "file": doc,
                "favicon": apps[0].favicon,
                "app_name": apps[0].name,
                "action_name": apps[0].actions[0].name,
                "url": apps[0].actions[0].url
                + "WOPISrc="
                + get_settings().wopi_api_endpoint
                + "/wopi/files/"
                + file_id,
            }
        )
    return result
