from __future__ import annotations

from typing import Dict, Optional

from .base import StorageBackend
from .pacs import PacsBackend
from .s3 import S3Backend

_REGISTRY: Dict[str, StorageBackend] = {
    PacsBackend.store_type: PacsBackend(),
    S3Backend.store_type: S3Backend(),
}


def get_backend(store_type: str) -> Optional[StorageBackend]:
    """Return the backend for a coordinate ``type``, or None if unsupported."""
    return _REGISTRY.get(store_type)
