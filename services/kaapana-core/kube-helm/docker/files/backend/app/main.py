import os
from fastapi import FastAPI

from routes import router
from fastapi.staticfiles import StaticFiles
from repeat_timer import RepeatedTimer
from utils import get_extensions_list, charts_cached, helm_search_repo
import uvicorn
from fastapi.templating import Jinja2Templates

app = FastAPI(openapi_prefix=os.getenv('APPLICATION_ROOT', ''))

if __name__ == 'app.main':

    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.include_router(
        router,
    )

    if charts_cached == None:
        helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])

    rt = RepeatedTimer(5, get_extensions_list)

if __name__ == "__main__":

    app.mount("/static", StaticFiles(directory="/home/jonas/projects/kaapana/services/kaapana-core/kube-helm/docker/files/backend/app/static"), name="static")
    app.include_router(
        router,
    )

    if charts_cached == None:
        helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])

    rt = RepeatedTimer(5, get_extensions_list)
    uvicorn.run(app, host="0.0.0.0", port=5000)

# @app.on_event("startup")
# def on_startup_event():
# Use me only if you want me to be executed for each worker...
