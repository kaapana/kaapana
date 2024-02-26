import functools
from app.model.websockets import ConnectionManager
from app.model.documents import DocumentStore
from app.model.wopi import WOPI
from app.config import get_settings
from fastapi import Request, Depends


@functools.lru_cache()
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()


def get_access_token(request: Request):
    return request.headers.get("x-forwarded-access-token")


@functools.lru_cache()
def get_wopi() -> WOPI:
    return WOPI(get_settings().collabora_url + "/hosting/discovery")


@functools.lru_cache()
def get_document_store(x_auth_token: str = Depends(get_access_token)) -> DocumentStore:
    return DocumentStore(x_auth_token)
