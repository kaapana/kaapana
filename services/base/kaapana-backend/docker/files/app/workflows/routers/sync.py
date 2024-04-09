from typing import List
import logging

from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.orm import Session
from app.dependencies import get_db

from app.workflows import crud
from app.workflows import schemas
from app.workflows.utils import requests_retry_session
from app.config import settings
from urllib3.util import Timeout

logging.getLogger().setLevel(logging.INFO)

TIMEOUT_SEC = 5
TIMEOUT = Timeout(TIMEOUT_SEC)

router = APIRouter(tags=["sync"])

@router.get("/check-for-remote-updates")
def check_for_remote_updates(db: Session = Depends(get_db)):
    return crud.get_remote_updates(db, periodically=False)