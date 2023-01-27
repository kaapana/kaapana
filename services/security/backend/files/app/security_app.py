from fastapi import APIRouter, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from routers import api, devtests

router = APIRouter(redirect_slashes=True)
router.include_router(api.router)
router.include_router(devtests.router)

router.mount("/assets", StaticFiles(directory="./static/assets", html=True), name="vue-frontend")

templates = Jinja2Templates(directory="./static")

@router.get("/api")
def redirect_api_to_api_slash(request: Request):
    return RedirectResponse(f"{request.url}/")

@router.get("/{full_path:path}")
async def catch_all(request: Request, full_path: str):
    return templates.TemplateResponse("index.html", {"request": request})
