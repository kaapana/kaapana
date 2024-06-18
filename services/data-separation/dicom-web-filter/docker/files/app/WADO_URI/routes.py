from fastapi import APIRouter, Request
from ..proxy_request import proxy_request

router = APIRouter()

# WADO-RS routes


@router.get("/wado", tags=["WADO-RS"])
async def retrieve_instance(request: Request):
    return await proxy_request(request, "/wado", "GET")
