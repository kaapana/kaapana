import functools
from pathlib import Path
from app.model.websockets import ConnectionManager
from app.model.documents import DocumentStore
from app.model.wopi import WOPI
from app.config import get_settings


@functools.lru_cache()
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()


@functools.lru_cache()
def get_document_store() -> DocumentStore:
    return DocumentStore(Path(get_settings().document_root))


@functools.lru_cache()
def get_wopi() -> WOPI:
    return WOPI(get_settings().collabora_url + "/hosting/discovery")
