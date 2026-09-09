import logging
import time

from fastapi import APIRouter, HTTPException

from app import ingress_source
from app.config import get_settings
from app.menu import build_menu
from app.models import MenuResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# CACHE_TTL_SECONDS bounds list_ingress_for_all_namespaces() calls against the
# API server; every logged-in user can reach this endpoint, so `fresh` gets its
# own floor rather than trusting callers to debounce.
FRESH_MIN_AGE_SECONDS = 1

# single-worker deployment -> one process-wide cache
_menu: MenuResponse | None = None
_fetched_at: float = 0.0


@router.get("/menu", summary="Discovered menu structure")
async def get_menu(fresh: bool = False) -> MenuResponse:
    global _menu, _fetched_at
    max_age = FRESH_MIN_AGE_SECONDS if fresh else get_settings().CACHE_TTL_SECONDS
    if _menu is not None and time.monotonic() - _fetched_at < max_age:
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
