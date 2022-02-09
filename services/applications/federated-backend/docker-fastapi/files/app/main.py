import requests
from fastapi import Depends, FastAPI, Request
from .internal import admin
from .routers import remote
from .dependencies import get_query_token, get_token_header
from . import crud, models, schemas
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
    dependencies=[Depends(get_token_header)],
    responses={418: {"description": "I'm a teapot"}},
)


# app.include_router(
#     admin.router,
#     prefix="/admin",
#     tags=["admin"],
#     # dependencies=[Depends(get_token_header)],
#     responses={418: {"description": "I'm a admin"}},
# )
