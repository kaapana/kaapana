import os
from fastapi import FastAPI

from .routes import router
from fastapi.staticfiles import StaticFiles
from .repeat_timer import RepeatedTimer
from .utils import get_extensions_list, charts_cached, helm_search_repo

if __name__ == 'app.main':

    app = FastAPI(openapi_prefix=os.getenv('APPLICATION_ROOT', ''))

    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.include_router(
        router,
    )

    if charts_cached == None:
        helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])

    rt = RepeatedTimer(5, get_extensions_list)

# @app.on_event("startup")
# def on_startup_event():
# Use me only if you want me to be executed for each worker...