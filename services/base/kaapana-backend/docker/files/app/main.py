import requests
import urllib3
import os
import logging
from fastapi import Depends, FastAPI, Request

from .admin import routers as admin
from .experiments.routers import remote, client
from .monitoring import routers as monitoring
from .storage import routers as storage
from .users import routers as users
from .workflows import routers as workflows

from .dependencies import get_query_token, get_token_header
from .database import SessionLocal, engine
from .decorators import repeat_every
from .experiments import models
from .experiments.crud import get_remote_updates

models.Base.metadata.create_all(bind=engine)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.getLogger().setLevel(logging.INFO)

# app = FastAPI()
app = FastAPI()

@app.on_event("startup")
@repeat_every(seconds=float(os.getenv('REMOTE_SYNC_INTERVAL', 2.5)))
def periodically_get_remote_updates():
    with SessionLocal() as db:
        try:
            get_remote_updates(db, periodically=True)
        except Exception as e:
            logging.warning('Something went wrong updating')
            logging.warning(e)


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

# Not used yet
app.include_router(
    monitoring.router,
    prefix="/monitoring"
)

# Not used yet
app.include_router(
    users.router,
    prefix="/users"
)

# Not used yet
app.include_router(
    storage.router,
    prefix="/storage"
)

# Not used yet, probably overlap with client url
app.include_router(
    workflows.router,
    prefix="/workflows",
    responses={418: {"description": "workflows"}},
)