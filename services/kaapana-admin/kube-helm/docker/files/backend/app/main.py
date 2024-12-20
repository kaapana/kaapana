from os.path import dirname, join

import uvicorn
from config import settings
from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
from helm_helper import get_extensions_list
from prometheus_fastapi_instrumentator import Instrumentator
from routes import router

from middlewares import SanitizeBodyInputs, SanitizeQueryParams

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


if __name__ == "__main__":
    get_extensions_list()

    # if charts_cached == None:
    #     helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])
    # rt = RepeatedTimer(5, get_extensions_list)

    uvicorn.run("main:app", host="127.0.0.1", port=5000, reload=True)
