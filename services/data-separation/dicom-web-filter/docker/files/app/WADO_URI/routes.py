from fastapi import APIRouter, Request
from ..proxy_request import proxy_request
from ..config import DICOMWEB_BASE_URL_WADO_URI

router = APIRouter()

# WADO-RS routes


@router.get("/wado", tags=["WADO-URI"])
async def retrieve_instance(request: Request):

    # TODO: Ensure that the query is only executed within the series that are mapped to the project (or studies if whole studies are mapped to the project)

    return await proxy_request(request, "", "GET", DICOMWEB_BASE_URL_WADO_URI)
