from fastapi import FastAPI
from .aii.routes import router as aii_router
from .projects.routes import router as projects_router

from .database import engine
from .models import Base

Base.metadata.create_all(engine)

app = FastAPI(root_path="", title="access-information-interface", docs_url="/docs")
app.openapi_version = "3.0.0"


app.include_router(aii_router, prefix="/aii")
app.include_router(projects_router, prefix="/projects")
