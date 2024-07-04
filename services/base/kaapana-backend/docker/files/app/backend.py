import logging
import os
import traceback

import psutil
import requests
import urllib3
from fastapi import Depends, FastAPI, Request

from . import middlewares
from .admin import routers as admin
from .database import SessionLocal, engine
from .datasets import routers
from .decorators import repeat_every
from .monitoring import routers as monitoring
from .storage import routers as storage
from .users import routers as users
from .workflows import models
from .workflows.crud import sync_states_from_airflow
from .workflows.routers import client, remote

models.Base.metadata.create_all(bind=engine)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.getLogger().setLevel(logging.INFO)

app = FastAPI(root_path="/kaapana-backend")

# sanitize user inputs from the POST and PUT body
app.add_middleware(middlewares.SanitizeBodyInputs)

# sanitze user inputs from the query parameters in get requests
app.add_middleware(middlewares.SanitizeQueryParams)

# Adds security headers to the requests
app.add_middleware(middlewares.SecurityMiddleware)


@app.on_event("startup")
@repeat_every(seconds=float(os.getenv("AIRFLOW_SYNC_INTERVAL", 5.0)))
def periodically_sync_states_from_airflow():
    # From: https://github.com/dmontagu/fastapi-utils/issues/230
    # In the future also think about integrating celery, this might help with the issue of repeated execution: https://testdriven.io/blog/fastapi-and-celery/
    parent_process = psutil.Process(os.getppid())
    children = parent_process.children(recursive=True)  # List of all child processes
    if children[0].pid == os.getpid():
        with SessionLocal() as db:
            try:
                sync_states_from_airflow(db, status="queued", periodically=True)
                sync_states_from_airflow(db, status="scheduled", periodically=True)
                sync_states_from_airflow(db, status="running", periodically=True)
            except Exception as e:
                logging.warning(
                    "Something went wrong updating in crud.sync_states_from_airflow()"
                )
                logging.warning(traceback.format_exc())


app.include_router(
    admin.router,
)

app.include_router(
    client.router,
    prefix="/client",
    responses={418: {"description": "I'm the clients backend..."}},
)

app.include_router(routers.router, prefix="/dataset")
app.include_router(monitoring.router, prefix="/monitoring")
