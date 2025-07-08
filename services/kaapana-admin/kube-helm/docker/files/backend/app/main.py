from os.path import dirname, join

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from kaapanapy.logger import get_logger
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings, timeouts
from .middlewares import SanitizeBodyInputs, SanitizeQueryParams
from .routes import router

logger = get_logger(__name__)

logger.info("Timeouts: %s", timeouts.model_dump_json())
logger.info("Settings: %s", settings.model_dump_json())

app = FastAPI(title="Kube-Helm API", root_path=settings.application_root)

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
