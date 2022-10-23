import requests
import urllib3
import os
from fastapi import Depends, FastAPI, Request

from .admin import routers as admin
from .extensions import routers as extensions
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

# app = FastAPI()
app = FastAPI()

@app.on_event("startup")
@repeat_every(seconds=float(os.getenv('REMOTE_SYNC_INTERVAL', 2.5)))
def periodically_get_remote_updates():
    with SessionLocal() as db:
        try:
            get_remote_updates(db, periodically=True)
        except Exception as e:
            print('Something went wrong updating')
            print(e)


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
    extensions.router,
    prefix="/extensions"
)

app.include_router(
    monitoring.router,
    prefix="/monitoring"
)

app.include_router(
    users.router,
    prefix="/users"
)

app.include_router(
    storage.router,
    prefix="/storage"
)

app.include_router(
    workflows.router,
    prefix="/workflows",
    responses={418: {"description": "workflows"}},
)