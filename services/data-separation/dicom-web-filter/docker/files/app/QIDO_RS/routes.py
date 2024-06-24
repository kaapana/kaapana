from fastapi import APIRouter, Request
from ..proxy_request import proxy_request

router = APIRouter()


@router.get("/studies", tags=["QIDO-RS"])
async def query_studies(request: Request):
    return await proxy_request(request, "/studies", "GET")


@router.get("/studies/{study}/series", tags=["QIDO-RS"])
async def query_series(study: str, request: Request):
    return await proxy_request(request, f"/studies/{study}/series", "GET")


@router.get("/studies/{study}/series/{series}/instances", tags=["QIDO-RS"])
async def query_instances(study: str, series: str, request: Request):
    return await proxy_request(
        request, f"/studies/{study}/series/{series}/instances", "GET"
    )
