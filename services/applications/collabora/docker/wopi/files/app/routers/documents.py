from app.config import get_settings
from app.dependencies import get_minio_client, get_project_bucket, get_wopi
from app.model.documents import encode_file_id, find_documents
from app.model.wopi import WOPI, editor_url
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(tags=["docs"])


@router.get("/")
def read_documents(
    bucket: str = Depends(get_project_bucket),
    wopi_srv: WOPI = Depends(get_wopi),
    minio=Depends(get_minio_client),
):
    if not wopi_srv.apps:
        raise HTTPException(503, "Collabora is not available yet, no document editor was discovered")

    settings = get_settings()
    result = []
    for doc in find_documents(minio, bucket, wopi_srv.supported_extensions(), settings.document_path_ignore_regex):
        match = wopi_srv.match(doc.extension)
        if match is None:
            continue
        file_id = encode_file_id(doc.bucket, doc.path)
        result.append(
            {
                "file_id": file_id,
                "file": {
                    "bucket": doc.bucket,
                    "path": doc.path,
                    "extension": doc.extension,
                    "modification_time": doc.modification_time,
                    "size": doc.size,
                },
                "favicon": match.app.favicon,
                "app_name": match.app.name,
                "action_name": match.action.name,
                "url": editor_url(match.action.url, f"{settings.wopi_api_endpoint}/wopi/files/{file_id}"),
            }
        )
    return result
