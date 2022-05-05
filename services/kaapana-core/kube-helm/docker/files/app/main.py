import os
from fastapi import FastAPI

from .routes import router
from fastapi.staticfiles import StaticFiles


app = FastAPI(openapi_prefix=os.getenv('APPLICATION_ROOT', ''))

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(
    router,
)
