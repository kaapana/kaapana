from fastapi import APIRouter, Request, Depends
from ..proxy_request import proxy_request
from ..database import get_session
from . import crud
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/studies", tags=["QIDO-RS"])
async def query_studies(request: Request, session: AsyncSession = Depends(get_session)):

    # Retrieve studies mapped to the project
    studies = set(await crud.get_all_studies_mapped_to_project(session, 1))

    # Adjust query parameters
    query_params = dict(request.query_params)
    for uid in studies:
        query_params.setdefault("StudyInstanceUID", []).append(uid)

    request._query_params = query_params

    return await proxy_request(request, "/studies", "GET")


@router.get("/studies/{study}/series", tags=["QIDO-RS"])
async def query_series(study: str, request: Request):

    # TODO: Only return series of the study that are mapped to the project

    return await proxy_request(request, f"/studies/{study}/series", "GET")


@router.get("/studies/{study}/series/{series}/instances", tags=["QIDO-RS"])
async def query_instances(study: str, series: str, request: Request):

    # TODO: Only return instances of the series that are mapped to the project (Filtering is on series level)

    return await proxy_request(
        request, f"/studies/{study}/series/{series}/instances", "GET"
    )
