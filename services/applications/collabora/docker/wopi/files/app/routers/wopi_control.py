from app.dependencies import get_wopi
from app.model.wopi import WOPI
from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

router = APIRouter(tags=["wopi-discover"])


@router.get("/apps")
async def read_wopi_apps(wopi_srv: WOPI = Depends(get_wopi)):
    return wopi_srv.apps


@router.post("/apps/update")
async def update_wopi_apps(wopi_srv: WOPI = Depends(get_wopi)):
    await run_in_threadpool(wopi_srv.fetch_apps)
    return wopi_srv.apps
