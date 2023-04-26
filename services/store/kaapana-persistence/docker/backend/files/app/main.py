import logging
import json

from glob import glob
from pathlib import Path
from fastapi import FastAPI, Depends

from .config import get_settings
from .dependencies import get_schema_service
from .routers.health import router as health_router
from .routers.schema import router as schema_router
from .routers.object import router as object_router
from .routers.urn import router as urn_router
from .routers.dicomweb import router as dicomweb_router
from .routers.cas import router as cas_router
from .routers.mnt import router as mnt_router
from .logger import get_logger, function_logger_factory

if get_settings().dev:
    logger = get_logger(__name__, logging.DEBUG)
else:
    logger = get_logger(__name__, logging.INFO)


app = FastAPI(title=get_settings().app_name, docs_url="/")

if get_settings().dev:
    logger.info(f"Persistence Layer is running in dev mode")
    from fastapi.middleware.cors import CORSMiddleware

    origins = [
        "http://localhost",
        "http://localhost:8080",
        "http://localhost:4173",
        "http://localhost:3000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("startup")
async def load_schemas():
    settings = get_settings()
    schema_service = get_schema_service()
    logger.info(f"Loading JSON Schemas from {settings.schema_folder}")
    for schema_file in glob(str(Path(settings.schema_folder) / "*.schema.json")):
        logger.info("Loading %s", schema_file)
        try:
            with open(schema_file) as fd:
                data = json.load(fd)
                await schema_service.register(data)
        except json.decoder.JSONDecodeError as e:
            logger.error("Invalid Json in %s", schema_file, exc_info=1)
        except Exception as e:
            logger.error("Failed to register schema %s", schema_file, exc_info=1)

    logger.info("Loading of schemas done")


app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(urn_router, prefix="/urn", tags=["urn"])
app.include_router(schema_router, prefix="/schema", tags=["persistence"])
app.include_router(object_router, prefix="/object", tags=["persistence"])
app.include_router(cas_router, prefix="/cas", tags=["cas"])
app.include_router(dicomweb_router, prefix="/dicomweb", tags=["dicom"])
# app.include_router(mnt_router, prefix="/maintenance", tags=["maintenance"])
