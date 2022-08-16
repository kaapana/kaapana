import os
from fastapi import FastAPI

from routes import router
from fastapi.staticfiles import StaticFiles
from repeat_timer import RepeatedTimer
from utils import get_extensions_list, charts_cached, helm_search_repo
import uvicorn
from fastapi.templating import Jinja2Templates
from os.path import basename, dirname, join

url_prefix = os.getenv('APPLICATION_ROOT', '')
app = FastAPI(openapi_prefix=url_prefix)

app.mount("/static", StaticFiles(directory=join(dirname(str(__file__)), "static")), name="static")

app.include_router(
    router,
)
if charts_cached == None:
    helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])

rt = RepeatedTimer(5, get_extensions_list)

# if __name__ == 'app.main':

if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=5000)

# @app.on_event("startup")
# def on_startup_event():
# Use me only if you want me to be executed for each worker...
