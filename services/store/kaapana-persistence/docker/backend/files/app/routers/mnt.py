from fastapi import APIRouter, HTTPException, Depends
from app.dependencies import get_db
from app.logger import get_logger, function_logger_factory

router = APIRouter()


@router.delete("/cache", status_code=204, summary="Destroys caching database")
async def delete_cache():
    pass


@router.get(
    "/cache/warmup", summary="Read complete CAS and fill caching database (Expensive!)"
)
async def warmup_cache():
    pass


@router.delete("/prune", status_code=204, summary="Remove")
async def prune():
    pass
