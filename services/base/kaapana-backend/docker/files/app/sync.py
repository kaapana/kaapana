import urllib3
import os
import logging
import traceback
import psutil

from fastapi import FastAPI

from .workflows.routers import sync

from .database import SessionLocal, engine
from .decorators import repeat_every
from .workflows import models
from .workflows.crud import (
    get_remote_updates,
)

from . import middlewares

models.Base.metadata.create_all(bind=engine)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.getLogger().setLevel(logging.INFO)

app = FastAPI(root_path="/kaapana-sync")

# sanitize user inputs from the POST and PUT body
app.add_middleware(middlewares.SanitizeBodyInputs)

# sanitze user inputs from the query parameters in get requests
app.add_middleware(middlewares.SanitizeQueryParams)


@app.get("/health-check")
def health_check():
    return {f"Kaapana sync backend is up and running!"}

@app.on_event("startup")
@repeat_every(seconds=float(os.getenv("REMOTE_SYNC_INTERVAL", 2.5)))
def periodically_get_remote_updates():
    # From: https://github.com/dmontagu/fastapi-utils/issues/230
    # In the future also think about integrating celery, this might help with the issue of repeated execution: https://testdriven.io/blog/fastapi-and-celery/
    parent_process = psutil.Process(os.getppid())
    children = parent_process.children(recursive=True)  # List of all child processes
    if children[0].pid == os.getpid():
        with SessionLocal() as db:
            try:
                get_remote_updates(db, periodically=True)
                logging.info(
                    "Checking for remote updates"
                ) 
            except Exception as e:
                logging.warning(
                    "Something went wrong updating in crud.get_remote_updates()"
                )
                logging.warning(traceback.format_exc())

app.include_router(
    sync.router,
    prefix="/sync",
    responses={418: {"description": "I'm the sync backend..."}},
)
