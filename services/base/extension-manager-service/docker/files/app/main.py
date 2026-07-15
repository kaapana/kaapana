from contextlib import asynccontextmanager

from fastapi import FastAPI
from v1.routers.installation import endpoints as installation_router
from v1.routers.repository import endpoints as repository_router
from v1.services.database.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Extension Manager Service",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.0.1",
    openapi_version="3.2.0",
    openapi_tags=[
        {
            "name": "extensions",
            "description": "Managing extension repositories and installation.",
        }
    ],
    lifespan=lifespan,
)

app.include_router(repository_router.router)
app.include_router(installation_router.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
