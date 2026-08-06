import logging
import time

from fastapi import APIRouter, HTTPException

from app import ingress_source
from app.config import get_settings
from app.menu import build_menu
from app.models import MenuResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# single-worker deployment -> one process-wide cache
_menu: MenuResponse | None = None
_fetched_at: float = 0.0


@router.get("/menu", summary="Discovered menu structure")
async def get_menu() -> MenuResponse:
    global _menu, _fetched_at
    if (
        _menu is not None
        and time.monotonic() - _fetched_at < get_settings().CACHE_TTL_SECONDS
    ):
        return _menu
    try:
        ingresses = await ingress_source.list_ingresses()
    except Exception:
        logger.exception("ingress refresh failed")
        if _menu is not None:
            # menu availability beats freshness: serve stale over an empty drawer
            return _menu
        raise HTTPException(status_code=503, detail="kubernetes API unavailable")
    _menu = build_menu(ingresses)
    _fetched_at = time.monotonic()
    return _menu
