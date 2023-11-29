# from fastapi import Depends, FastAPI, Request

import requests
import urllib3
import os
import logging
import traceback
import psutil

from fastapi import Depends, FastAPI, Request

# from .admin import routers as admin
# from .datasets import routers
# from .workflows.routers import remote, client
# from .monitoring import routers as monitoring
# from .storage import routers as storage
# from .users import routers as users

# from .dependencies import get_query_token, get_token_header
# from .database import SessionLocal, engine
# from .decorators import repeat_every
# from .workflows import models
# from .workflows.crud import (
    # get_remote_updates,
    # sync_states_from_airflow,
    # sync_n_clean_qsr_jobs_with_airflow,
# )

import models

# models.Base.metadata.create_all(bind=engine)

# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# logging.getLogger().setLevel(logging.INFO)

app = FastAPI(root_path="/spe-backend")

# models.Base.metadata.create_all(bind=engine)

# app = FastAPI()

# TODO erase dirty dev
# os.environ[DATABASE_URL]

@app.get("/")
async def root():
    return {"message": "Im the spe backend"}

# @app.get("")