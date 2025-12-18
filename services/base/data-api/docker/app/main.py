from fastapi import FastAPI

from .api.v1 import router as api_v1_router


def create_app() -> FastAPI:
    app = FastAPI(title="Data API", version="1.0.0")

    app.include_router(api_v1_router, prefix="/v1")
    return app


app = create_app()
