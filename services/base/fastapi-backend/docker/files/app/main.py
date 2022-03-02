import requests
from fastapi import Depends, FastAPI, Request

from .internal import admin
from .routers import remote, extensions, monitoring, users, storage
from .dependencies import get_query_token, get_token_header
from . import crud, models
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)


app = FastAPI()

app.include_router(
    admin.router,
)
app.include_router(
    remote.router,
    prefix="/remote",
    # tags=["admin"],
    # dependencies=[Depends(get_token_header)],
    responses={418: {"description": "I'm a teapot"}},
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
# app.include_router(
#     admin.router,
#     prefix="/admin",
#     tags=["admin"],
#     # dependencies=[Depends(get_token_header)],
#     responses={418: {"description": "I'm a admin"}},
# )
