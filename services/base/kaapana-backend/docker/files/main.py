import requests
from fastapi import Depends, FastAPI, Request

from .admin import routers as admin
from .extensions import routers as extensions
from .federated import routers as federated
from .monitoring import routers as monitoring
from .storage import routers as storage
from .users import routers as users
from .workflows import routers as workflows

from .dependencies import get_query_token, get_token_header
from .database import SessionLocal, engine

# models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(
    admin.router,
)
app.include_router(
    federated.router,
    prefix="/federated",
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

app.include_router(
    workflows.router,
    prefix="/workflows",
    tags=["workflows"],
    responses={418: {"description": "workflows"}},
)