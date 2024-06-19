from fastapi import APIRouter, Request
from ..proxy_request import proxy_request
from ..config import DICOMWEB_BASE_URL_WADO_URI

router = APIRouter()

# WADO-RS routes


@router.get("/wado", tags=["WADO-URI"])
async def retrieve_instance(request: Request):
    return await proxy_request(request, "", "GET", DICOMWEB_BASE_URL_WADO_URI)
