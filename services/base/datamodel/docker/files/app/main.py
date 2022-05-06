import requests
from fastapi import Depends, FastAPI, Request

from .internal import admin
from .routers import remote, extensions, monitoring, users, storage, workflow
from .dependencies import get_query_token, get_token_header
from . import crud, models
from .database import SessionLocal, engine
from datamodel import DM
models.Base.metadata.create_all(bind=engine)



app = FastAPI()


DM.setup_db(app)
app.datamodel = DM


app.include_router(graphql_app, prefix="/graphql")