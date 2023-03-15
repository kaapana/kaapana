from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.routing import Mount as Mount
from security_app import router as security_app_router
from helpers.logger import get_logger
import logging
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

logger = get_logger(level=logging.INFO)

app = FastAPI(root_path="/security")
app.include_router(security_app_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
    logger.error(f"{request}: {exc_str}")
    content = {"status_code": 10422, "message": exc_str, "data": None}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


app.mount("/assets", StaticFiles(directory="./static/assets", html=True), name="vue-frontend")

templates = Jinja2Templates(directory="./static")


@app.get("/{full_path:path}", include_in_schema=False)
async def catch_all(request: Request, full_path: str):
    return templates.TemplateResponse("index.html", {"request": request})
