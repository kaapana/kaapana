from __future__ import annotations

import logging
from typing import Iterator, Optional, Tuple

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from app.models import DownloadItem, DownloadRequest
from app.services.archive import stream_tar, stream_zip
from app.services.backends import get_backend

logger = logging.getLogger(__name__)

router = APIRouter()


def _resolve_token(
    x_forwarded_access_token: Optional[str], authorization: Optional[str]
) -> Optional[str]:
    """Prefer the forwarded token, else the bearer in Authorization."""
    if x_forwarded_access_token:
        return x_forwarded_access_token
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[len("bearer ") :].strip()
    return None


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _iter_files(
    items: list[DownloadItem], access_token: Optional[str]
) -> Iterator[Tuple[str, bytes]]:
    for item in items:
        for coordinate in item.coordinates:
            backend = get_backend(coordinate.type)
            for relpath, content in backend.fetch(coordinate, access_token):
                yield f"{item.id}/{relpath}", content


@router.post("/download")
def download(
    request: DownloadRequest,
    x_forwarded_access_token: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
) -> StreamingResponse:
    # Validate every coordinate type up front so unsupported types fail with a
    # clean 400 before the stream starts (mid-stream errors can't change status).
    for item in request.items:
        for coordinate in item.coordinates:
            if get_backend(coordinate.type) is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"No storage backend for coordinate type '{coordinate.type}'",
                )

    token = _resolve_token(x_forwarded_access_token, authorization)

    files = _iter_files(request.items, token)
    if request.format == "zip":
        return StreamingResponse(
            stream_zip(files),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=download.zip"},
        )
    return StreamingResponse(
        stream_tar(files),
        media_type="application/x-tar",
        headers={"Content-Disposition": "attachment; filename=download.tar"},
    )
