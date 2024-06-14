from fastapi import FastAPI
from .aii.routes import router as aii_router
from .projects.routes import router as projects_router
from fastapi.responses import FileResponse

from .database import engine
from .models import Base

Base.metadata.create_all(engine)

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
)

app.include_router(aii_router, prefix="/aii")
app.include_router(projects_router, prefix="/projects")
