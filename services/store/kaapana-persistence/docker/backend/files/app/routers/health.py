from fastapi import APIRouter, Depends
from app.config import get_settings
import datetime

router = APIRouter()


@router.get("/")
def health_check(settings=Depends(get_settings)):
    return {
        "status": "online",
        "time": datetime.datetime.now(),
        "app": settings.app_name,
    }
