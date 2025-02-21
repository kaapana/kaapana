import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)


app = FastAPI(
    root_path="/notifications-api",
    title="notifications-api",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
)
