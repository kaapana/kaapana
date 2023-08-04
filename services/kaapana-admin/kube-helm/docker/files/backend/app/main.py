from os.path import basename, dirname, join
import uvicorn
import logging

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.logger import logger

from utils import helm_search_repo
from routes import router
from repeat_timer import RepeatedTimer
from config import settings
from helm_helper import get_extensions_list

app = FastAPI(title="Kube-Helm API", root_path=settings.application_root)

app.include_router(router)
app.mount(
    "/static",
    StaticFiles(directory=join(dirname(str(__file__)), "static")),
    name="static",
)


@app.on_event("startup")
async def startup_event():
    log_level = settings.log_level.upper()
    if log_level == "DEBUG":
        log_level = logging.DEBUG
    elif log_level == "INFO":
        log_level = logging.INFO
    elif log_level == "WARNING":
        log_level = logging.WARNING
    elif log_level == "ERROR":
        log_level = logging.ERROR
    elif log_level == "CRITICAL":
        log_level = logging.CRITICAL
    else:
        logging.error(
            f"Unknown log-level: {settings.log_level} -> Setting log-level to 'INFO'"
        )
        log_level = logging.INFO

    gunicorn_logger = logging.getLogger("gunicorn.error")
    logger.handlers = gunicorn_logger.handlers
    logger.setLevel(log_level)
    logger.info(f"FastAPI logger level set to {logging.getLevelName(log_level)}")
    logger.info(f"{settings=}")


if __name__ == "__main__":
    get_extensions_list()

    # if charts_cached == None:
    #     helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])
    # rt = RepeatedTimer(5, get_extensions_list)

    uvicorn.run("main:app", host="127.0.0.1", port=5000, log_level="info", reload=True)
