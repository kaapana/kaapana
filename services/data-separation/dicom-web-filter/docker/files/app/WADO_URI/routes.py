from ..proxy_request import proxy_request
from ..database import get_session
from . import crud
from ..config import DEFAULT_PROJECT_ID, DICOMWEB_BASE_URL, DICOMWEB_BASE_URL_WADO_URI
from sqlalchemy.ext.asyncio import AsyncSession
import re
import httpx
import debugpy
from fastapi import APIRouter, Request, Depends, Response
from fastapi.responses import StreamingResponse

router = APIRouter()

# WADO-RS routes


@router.get("/wado", tags=["WADO-URI"])
async def retrieve_instance(
    request: Request, session: AsyncSession = Depends(get_session)
):

    # check if StudyInstanceUID is in the query parameters
    if "StudyInstanceUID" in request.query_params:
        pass

    # check if SeriesInstanceUID is in the query parameters
    if "SeriesInstanceUID" in request.query_params:
        pass

    return await proxy_request(request, "", "GET", DICOMWEB_BASE_URL_WADO_URI)
