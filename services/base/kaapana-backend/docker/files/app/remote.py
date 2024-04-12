import urllib3
import logging

from fastapi import Depends, FastAPI

from .workflows.routers import remote

from .dependencies import get_query_token, get_token_header
from .database import SessionLocal, engine
from .workflows import models
from . import middlewares

models.Base.metadata.create_all(bind=engine)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.getLogger().setLevel(logging.INFO)

app = FastAPI(root_path="/kaapana-remote")

# sanitize user inputs from the POST and PUT body
app.add_middleware(middlewares.SanitizeBodyInputs)

# sanitze user inputs from the query parameters in get requests
app.add_middleware(middlewares.SanitizeQueryParams)

app.include_router(
    remote.router,
    prefix="/remote",
    dependencies=[Depends(get_token_header)],
    responses={418: {"description": "I'm the remote backend..."}},
)