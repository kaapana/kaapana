from fastapi import APIRouter
import httpx
import logging
from helpers.resources import LOGGER_NAME
from helpers.logger import get_logger

logger = get_logger(f"{LOGGER_NAME}.devtests", logging.INFO)

router = APIRouter(prefix=f"/tests", redirect_slashes=True)

@router.get("/ping-wazuh")
async def get_ping_wazuh():
    result = await httpx.get("https://security-wazuh-service.services.svc:55000/")
    logger.debug(result)
    return result.text

@router.get("/")
def get_test():
    return {"Hello": "World"}
