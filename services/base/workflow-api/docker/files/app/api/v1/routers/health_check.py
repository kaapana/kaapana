import logging

from app.dependencies import get_async_db
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health-db", tags=["health"])
async def db_health(db: AsyncSession = Depends(get_async_db)):
    """Lightweight health endpoint. Checks database connectivity using the standard session dependency."""
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        logger.exception("Health check DB query failed")

    code = 200 if db_ok else 503
    return JSONResponse(status_code=code, content={"database": db_ok})


@router.get("/health", tags=["health"])
async def health():
    """Lightweight health endpoint."""
    return JSONResponse(status_code=200, content={"status": "ok"})
