from fastapi import APIRouter, FastAPI
from routes import router
from fastapi.staticfiles import StaticFiles
from repeat_timer import RepeatedTimer
from utils import get_extensions_list, charts_cached, helm_search_repo
import uvicorn
from os.path import basename, dirname, join
from config import settings
from fastapi.middleware.cors import CORSMiddleware
import logging
import helm_helper

app = FastAPI(title="Kube-Helm API", root_path=settings.application_root)
origins = [
    "https://e230-nb03wl",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.mount("/static", StaticFiles(directory=join(dirname(str(__file__)), "static")), name="static")


@app.on_event("startup")
async def startup_event():
    logger = logging.getLogger("uvicorn")
    if settings.log_level == "DEBUG":
        log_level = logging.DEBUG
    elif settings.log_level == "INFO":
        log_level = logging.INFO
    elif settings.log_level == "WARNING":
        log_level = logging.WARNING
    elif settings.log_level == "ERROR":
        log_level = logging.ERROR
    elif settings.log_level == "CRITICAL":
        log_level = logging.CRITICAL
    else:
        logging.error(f"Unknown log-level: {settings.log_level} -> Setting log-level to 'INFO'")
        log_level = logging.INFO

    logger.setLevel(log_level)

if __name__ == "__main__":
    helm_helper.get_extensions_list()

    # if charts_cached == None:
    #     helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])
    # rt = RepeatedTimer(5, get_extensions_list)

    uvicorn.run("main:app", host="127.0.0.1", port=5000, log_level="info", reload=True)
