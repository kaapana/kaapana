import requests
import urllib3
import os
import logging
import traceback
from fastapi import Depends, FastAPI, Request

from .m2olie import routers as m2olie

logging.getLogger().setLevel(logging.INFO)

# app = FastAPI()
app = FastAPI()

app.include_router(m2olie.router)
