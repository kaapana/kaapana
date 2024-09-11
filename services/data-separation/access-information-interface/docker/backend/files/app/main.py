import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import init_scripts
from .aii.routes import router as aii_router
from .database import async_engine
from .models import Base
from .projects.routes import router as projects_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_scripts.initial_database_population()
    # await init_scripts.init_opensearch()
    # await init_scripts.init_minio()
    # await init_scripts.init_namespace()
    yield  # This yield separates startup from shutdown code
    # Code here would run after the application stops


tags_metadata = [
    {
        "name": "Projects",
        "description": "Create, delete and modify projects",
    },
    {
        "name": "Aii",
        "description": "Retrive authorization related information",
    },
]

app = FastAPI(
    root_path="/aii",
    title="access-information-interface",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

app.include_router(aii_router, prefix="/aii")
app.include_router(projects_router, prefix="/projects")
