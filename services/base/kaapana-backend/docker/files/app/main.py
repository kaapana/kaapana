import logging
import os
import traceback

import psutil
import urllib3
from fastapi import Depends, FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from . import middlewares
from .admin import routers as admin
from .database import SessionLocal, engine
from .datasets import routers
from .decorators import only_one_process, repeat_every
from .dependencies import get_token_header
from .monitoring import routers as monitoring
from .settings import routers as settings
from .workflows import models
from .workflows.crud import get_remote_updates, sync_states_from_airflow
from .workflows.routers import client, remote
from .storage import routers as storage
from . import middlewares

models.Base.metadata.create_all(bind=engine)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.getLogger().setLevel(logging.INFO)

app = FastAPI(root_path="/kaapana-backend")

# sanitize user inputs from the POST and PUT body
app.add_middleware(middlewares.SanitizeBodyInputs)

# sanitze user inputs from the query parameters in get requests
app.add_middleware(middlewares.SanitizeQueryParams)


@app.on_event("startup")
@repeat_every(seconds=float(os.getenv("REMOTE_SYNC_INTERVAL", 2.5)))
@only_one_process(lock_file="/tmp/remote_sync.lock")
def periodically_get_remote_updates():
    # From: https://github.com/dmontagu/fastapi-utils/issues/230
    # In the future also think about integrating celery, this might help with the issue of repeated execution: https://testdriven.io/blog/fastapi-and-celery/
    with SessionLocal() as db:
        try:
            get_remote_updates(db, periodically=True)
        except Exception:
            logging.warning(
                "Something went wrong updating in crud.get_remote_updates()"
            )
            logging.warning(traceback.format_exc())


@app.on_event("startup")
@repeat_every(seconds=float(os.getenv("AIRFLOW_SYNC_INTERVAL", 10.0)))
@only_one_process()
def periodically_sync_states_from_airflow():
    with SessionLocal() as db:
        try:
            sync_states_from_airflow(db, status="queued", periodically=True)
            sync_states_from_airflow(db, status="scheduled", periodically=True)
            sync_states_from_airflow(db, status="running", periodically=True)
        except Exception:
            logging.warning(
                "Something went wrong updating in crud.sync_states_from_airflow()"
            )
            logging.warning(traceback.format_exc())


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
app.include_router(
    settings.router,
    prefix="/settings",
    responses={418: {"description": "I'm the settings backend..."}},
)

app.include_router(routers.router, prefix="/dataset")
app.include_router(monitoring.router, prefix="/monitoring")

# # Not used yet
# app.include_router(users.router, prefix="/users")

# # Not used yet
app.include_router(
    storage.router,
    prefix="/storage",
    responses={418: {"description": "I'm the storage backend..."}},
)
Instrumentator().instrument(app).expose(app)
