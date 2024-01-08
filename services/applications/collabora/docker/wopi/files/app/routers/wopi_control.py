from fastapi import APIRouter, Depends
from app.model.wopi import WOPI
from app.dependencies import get_wopi

router = APIRouter(tags=["wopi-discover"])


@router.get("/apps")
async def read_wopi_apps(wopi_srv: WOPI = Depends(get_wopi)):
    return wopi_srv.apps


@router.post("/apps/update")
async def update_wopi_apps(wopi_srv: WOPI = Depends(get_wopi)):
    wopi_srv.fetch_apps()
