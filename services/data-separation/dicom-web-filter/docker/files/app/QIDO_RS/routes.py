from fastapi import APIRouter, Request
from ..proxy_request import proxy_request

router = APIRouter()


@router.get("/studies", tags=["QIDO-RS"])
async def query_studies(request: Request):

    #TODO: Only return studies that are mapped to the project

    return await proxy_request(request, "/studies", "GET")


@router.get("/studies/{study}/series", tags=["QIDO-RS"])
async def query_series(study: str, request: Request):

    #TODO: Only return series of the study that are mapped to the project

    return await proxy_request(request, f"/studies/{study}/series", "GET")


@router.get("/studies/{study}/series/{series}/instances", tags=["QIDO-RS"])
async def query_instances(study: str, series: str, request: Request):

    # TODO: Only return instances of the series that are mapped to the project (Filtering is on series level)

    return await proxy_request(
        request, f"/studies/{study}/series/{series}/instances", "GET"
    )
