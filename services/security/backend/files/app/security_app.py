from fastapi import APIRouter, Request
from routers import api

router = APIRouter(redirect_slashes=True)
router.include_router(api.router)
