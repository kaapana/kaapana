import os
from fastapi import Depends, FastAPI, Request

from .internal import admin
from .routers import remote, client, json_schemas
from .dependencies import get_query_token, get_token_header, get_db
from . import crud, models, schemas
from .database import SessionLocal, engine
from app.crontab import RepeatedTimer, execute_scheduled_jobs
from app.decorators import repeat_every
from app.utils import get_remote_updates

models.Base.metadata.create_all(bind=engine)


app = FastAPI(openapi_prefix=os.getenv('APPLICATION_ROOT', ''))

app.include_router(
    admin.router,
)
app.include_router(
    remote.router,
    prefix="/remote",
    # tags=["admin"],
    dependencies=[Depends(get_token_header)],
    responses={418: {"description": "I'm a teapot"}},
)
app.include_router(
    client.router,
    prefix="/client",
    # tags=["admin"],
    responses={418: {"description": "I'm a teapot"}},
)

app.include_router(
    json_schemas.router,
    prefix="/json-schemas",
    # tags=["admin"],
    responses={418: {"description": "I'm a teapot"}},
)


@app.on_event("startup")
@repeat_every(seconds=20)  # 1 hour
def periodically_get_remote_updates():
    print('Checking for updates!')
    with SessionLocal() as db:
        get_remote_updates(db, periodically=True)
