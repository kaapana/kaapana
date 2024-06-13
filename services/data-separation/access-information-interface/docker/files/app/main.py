from fastapi import FastAPI
from .routes import router
from .database import engine
from .models import Base

Base.metadata.create_all(engine)

app = FastAPI(root_path="",title="access-information-interface", docs_url="/docs")
app.openapi_version = "3.0.0"


app.include_router(router)
