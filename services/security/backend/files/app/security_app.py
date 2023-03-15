from fastapi import APIRouter, Request
from routers import api, devtests

router = APIRouter(redirect_slashes=True)
router.include_router(api.router)
router.include_router(devtests.router)
