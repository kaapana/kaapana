import requests
import urllib3
import os
import logging
import traceback
import psutil

from fastapi import Depends, FastAPI, Request

from .admin import routers as admin
from .datasets import routers
from .workflows.routers import remote, client
from .monitoring import routers as monitoring
from .storage import routers as storage
from .users import routers as users

from .dependencies import get_query_token, get_token_header
from .database import SessionLocal, engine
from .decorators import repeat_every
from .workflows import models
from .workflows.crud import (
    get_remote_updates,
    sync_states_from_airflow,
    sync_n_clean_qsr_jobs_with_airflow,
)

models.Base.metadata.create_all(bind=engine)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.getLogger().setLevel(logging.INFO)

app = FastAPI(root_path="/kaapana-backend")


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
            except Exception as e:
                logging.warning(
                    "Something went wrong updating in crud.get_remote_updates()"
                )
                logging.warning(traceback.format_exc())


@app.on_event("startup")
@repeat_every(seconds=float(os.getenv("AIRFLOW_SYNC_INTERVAL", 10.0)))
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


# @app.on_event("startup")
# @repeat_every(seconds=float(60.0))
# def periodically_sync_n_clean_qsr_jobs_with_airflow():
#     with SessionLocal() as db:
#         try:
#             sync_n_clean_qsr_jobs_with_airflow(db, periodically=True)
#         except Exception as e:
#             logging.warning('Something went wrong updating in crud.sync_n_clean_qsr_jobs_with_airflow()')
#             logging.warning(traceback.format_exc())


app.include_router(
    admin.router,
)

app.include_router(
    remote.router,
    prefix="/remote",
    dependencies=[Depends(get_token_header)],
    responses={418: {"description": "I'm the remote backend..."}},
)
app.include_router(
    client.router,
    prefix="/client",
    responses={418: {"description": "I'm the clients backend..."}},
)

app.include_router(routers.router, prefix="/dataset")
app.include_router(monitoring.router, prefix="/monitoring")

# # Not used yet
# app.include_router(users.router, prefix="/users")

# # Not used yet
# app.include_router(storage.router, prefix="/storage")
