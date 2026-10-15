from contextlib import asynccontextmanager
from os.path import dirname, join

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from kaapanapy.logger import get_logger
from prometheus_fastapi_instrumentator import Instrumentator

from . import auto_launch
from .config import settings, timeouts
from .middlewares import SanitizeBodyInputs, SanitizeQueryParams
from .routes import router

logger = get_logger(__name__)

logger.info("Timeouts: %s", timeouts.model_dump_json())
logger.info("Settings: %s", settings.model_dump_json())


@asynccontextmanager
async def lifespan(app):
    timer = auto_launch.start_reconciler()
    yield
    # The timer threads are not daemons; left running they keep the pod from
    # exiting on SIGTERM until it is killed.
    if timer:
        timer.stop()


app = FastAPI(
    title="Kube-Helm API", root_path=settings.application_root, lifespan=lifespan
)

# sanitize user inputs from the POST and PUT body
app.add_middleware(SanitizeBodyInputs)

# sanitze user inputs from the query parameters in get requests
app.add_middleware(SanitizeQueryParams)

app.include_router(router)
app.mount(
    "/static",
    StaticFiles(directory=join(dirname(str(__file__)), "static")),
    name="static",
)
Instrumentator().instrument(app).expose(app)
