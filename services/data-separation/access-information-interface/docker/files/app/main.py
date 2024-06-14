from fastapi import FastAPI
from .aii.routes import router as aii_router
from .projects.routes import router as projects_router
from .projects.crud import create_rights, create_roles
from .projects.schemas import CreateRight, CreateRole
from .database import async_session, async_engine
from .models import Base
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        await create_rights(session, CreateRight(name="read", description="Read rights", claim_key="read", claim_value="true"))
        await create_rights(session, CreateRight(name="write", description="Write rights", claim_key="write", claim_value="true"))
        await create_rights(session, CreateRight(name="delete", description="Delete rights", claim_key="delete", claim_value="true"))
        await create_roles(session, CreateRole(name="admin", description="Admin role"))
        await create_roles(session, CreateRole(name="read-only", description="Read only role"))
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
