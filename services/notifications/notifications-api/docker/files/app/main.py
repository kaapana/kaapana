import logging
from contextlib import asynccontextmanager

from app.database.queries import verify_postgres_conn
from fastapi import FastAPI, HTTPException

logger = logging.getLogger(__name__)


app = FastAPI(
    root_path="/notifications-api",
    title="notifications-api",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
)


@app.get("/check-db-connection")
async def check_db_connection():
    verified = await verify_postgres_conn()
    if verified:
        return {"status": "Database connection successful"}
    else:
        raise HTTPException(status_code=500, detail=f"Database connection failed")
