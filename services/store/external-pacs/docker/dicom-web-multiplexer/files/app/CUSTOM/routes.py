from fastapi import APIRouter, Request, Response
import logging


from fastapi.responses import Response

router = APIRouter()
logger = logging.getLogger(__name__)

@router.delete("/projects/{project_id}/studies/{study}", tags=["Custom"])
async def remove_study(
    project_id: int,
    study: str,
    request: Request,
):
    return Response(status_code=200)


@router.delete(
    "/projects/{project_id}/studies/{study}/series/{series}", tags=["Custom"]
)
async def remove_series(
    project_id: int,
    study: str,
    series: str,
    request: Request,
):
    return Response(status_code=200)