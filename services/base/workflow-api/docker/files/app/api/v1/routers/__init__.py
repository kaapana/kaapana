# app/api/v1/routers/__init__.py
from fastapi import HTTPException, status
from app.api.v1.services.errors import NotFoundError, BadRequestError, DependencyError, InternalError

def _map_service_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, BadRequestError):
        raise HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, DependencyError):
        raise HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, InternalError):
        raise HTTPException(status_code=500, detail=str(exc))
    # fallback
    raise HTTPException(status_code=500, detail="Internal server error")