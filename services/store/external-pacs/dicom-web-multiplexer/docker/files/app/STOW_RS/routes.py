import logging

import httpx
from app.database import get_session
from app.auth import authorize_headers
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from app.utils import rs_endpoint_url
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = logging.getLogger(__name__)


async def __stream_data(url: str, headers: dict, request: Request):
    """Stream the data to the DICOMWeb server.

    Args:
        request (Request): Request object
        url (str, optional): URL to send the request to. Defaults to "/studies".

    """

    async def data_streamer():
        async for chunk in request.stream():
            yield chunk

    async with httpx.AsyncClient(timeout=500) as client:
        async with client.stream(
            "POST",
            url,
            content=data_streamer(),
            headers=headers,
        ) as response:
            response.raise_for_status()

    # clinical_trial_protocol_info = json.loads(
    #     request.query_params.get("clinical_trial_protocol_info")
    # )

    # for series_instance_uid in clinical_trial_protocol_info:


@router.post("/studies", tags=["STOW-RS"])
async def store_instances(request: Request):
    """This endpoint is used to store data in the DICOMWeb server. The data is being mapped to the project and then streamed to the DICOMWeb server.

    Args:
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        Response: Response object
    """
    url = f"{rs_endpoint_url}/studies"
    headers = authorize_headers(request)
    await __stream_data(url=url, headers=headers, request=request)

    return Response(status_code=200)


@router.post("/studies/{study}", tags=["STOW-RS"])
async def store_instances_in_study(study: str, request: Request):
    url = f"{rs_endpoint_url}/studies/{study}"
    headers = authorize_headers(request)
    await __stream_data(url=url, headers=headers, request=request)

    return Response(status_code=200)
