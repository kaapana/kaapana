from fastapi import FastAPI
from .routes import router

app = FastAPI(title="access-information-interface", docs_url="/docs")


app.include_router(router)
