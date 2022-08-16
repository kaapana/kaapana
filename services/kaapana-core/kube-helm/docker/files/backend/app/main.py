from fastapi import APIRouter, FastAPI
from routes import router
from fastapi.staticfiles import StaticFiles
from repeat_timer import RepeatedTimer
from utils import get_extensions_list, charts_cached, helm_search_repo
import uvicorn
from os.path import basename, dirname, join
from config import settings
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Kube-Helm API", root_path=settings.application_root)
origins = [
    "https://e230-nb03wl"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__" or __name__ == 'app.main':

    app.mount("/static", StaticFiles(directory=join(dirname(str(__file__)), "static")), name="static")

    app.include_router(
        router,
    )
    if charts_cached == None:
        helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])

    rt = RepeatedTimer(5, get_extensions_list)


if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=5000, log_level="info", reload=False)
    # uvicorn.run("main:app", host="0.0.0.0", port=5000, log_level="info", reload=True)

# @app.on_event("startup")
# def on_startup_event():
# Use me only if you want me to be executed for each worker...
