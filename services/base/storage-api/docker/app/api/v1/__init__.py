from __future__ import annotations

import json
import logging
from typing import Iterator, List, Optional, Tuple

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import TypeAdapter, ValidationError

from app.models import DownloadItem, DownloadRequest, UploadResponse, UploadTarget
from app.services.archive import stream_tar, stream_zip
from app.services.backends import get_backend
from app.services.backends.base import StorageError

logger = logging.getLogger(__name__)

router = APIRouter()

_upload_target_adapter: TypeAdapter = TypeAdapter(UploadTarget)


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


@router.post("/upload", response_model=UploadResponse)
def upload(
    descriptor: str = Form(
        ...,
        description='JSON UploadTarget, e.g. {"store":"s3","bucket":"b","key_prefix":"p/"}',
    ),
    files: List[UploadFile] = File(...),
    x_forwarded_access_token: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
) -> UploadResponse:
    """Write uploaded files to the target store and return their coordinates.

    The mirror image of ``/download``: the storage-api moves bytes only; the
    caller records the returned coordinates on a new Data API entity. Bytes are
    written first, so a later failure to create the entity merely orphans a
    GC-able object rather than leaving a dangling coordinate.
    """
    try:
        target = _upload_target_adapter.validate_python(json.loads(descriptor))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid descriptor: {exc}")

    backend = get_backend(target.store)
    if backend is None:
        raise HTTPException(
            status_code=400,
            detail=f"No storage backend for store '{target.store}'",
        )

    token = _resolve_token(x_forwarded_access_token, authorization)

    payload = [(f.filename or "object", f.file.read()) for f in files]
    try:
        coordinates = backend.store(target, payload, token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except StorageError as exc:
        # Store-level failure with a known status (e.g. MinIO AccessDenied -> 403);
        # surface it instead of letting it fall through as a 500.
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    return UploadResponse(coordinates=coordinates)
