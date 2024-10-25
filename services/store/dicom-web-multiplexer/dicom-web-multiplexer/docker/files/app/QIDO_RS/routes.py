from app.auth import get_external_token
from app.logger import get_logger
from app.streaming_helpers import metadata_replace_stream
from app.utils import rs_endpoint_url
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

router = APIRouter()
logger = get_logger(__file__)


async def retrieve_studies(request: Request) -> Response:
    """Retrieve studies from the DICOM Web server.

    Args:
        request (Request): Request object

    Returns:
        response: Response object
    """
    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)
    auth_headers = {"Authorization": f"Bearer {token}"}
    includefield=""
    
    query_params = dict(request.query_params)
    if "includefield" in query_params:
        query_params["includefield"] += "," + includefield
    else:
        query_params["includefield"] = includefield

    return StreamingResponse(
        metadata_replace_stream(
            method="GET",
            url=f"{rs_endpoint}/studies",
            request=request,
            headers=auth_headers,
            query_params=query_params,
            search="/".join(rs_endpoint.split(":")[-1].split("/")[1:]).encode(),
            replace=b"dicom-web-filter",
        ),
        media_type="application/dicom+json",
    )


async def retrieve_series(study: str, request: Request) -> Response:
    """Retrieve series from the DICOM Web server.

    Args:
        study (str): Study Instance UID
        request (Request): Request object

    Returns:
        Response: Response object
    """
    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)
    auth_headers = {"Authorization": f"Bearer {token}"}
    includefield="StudyInstanceUID"
    
    query_params = dict(request.query_params)
    if "includefield" in query_params:
        query_params["includefield"] += "," + includefield
    else:
        query_params["includefield"] = includefield
    return StreamingResponse(
        metadata_replace_stream(
            method="GET",
            url=f"{rs_endpoint}/studies/{study}/series",
            request=request,
            headers=auth_headers,
            query_params=query_params,
            search="/".join(rs_endpoint.split(":")[-1].split("/")[1:]).encode(),
            replace=b"dicom-web-filter",
        ),
        media_type="application/dicom+json",
    )


async def retrieve_instances(study: str, series: str, request: Request) -> Response:
    """Retrieve instances from the DICOM Web server.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object

    Returns:
        Response: Response object
    """
    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)
    auth_headers = {"Authorization": f"Bearer {token}"}
    includefield="StudyInstanceUID,SeriesInstanceUID,Modality"
    query_params = dict(request.query_params)
    if "includefield" in query_params:
        query_params["includefield"] += "," + includefield
    else:
        query_params["includefield"] = includefield
    
    
            
    return StreamingResponse(
        metadata_replace_stream(
            method="GET",
            url=f"{rs_endpoint}/studies/{study}/series/{series}/instances",
            request=request,
            headers=auth_headers,
            query_params=query_params,
            search="/".join(rs_endpoint.split(":")[-1].split("/")[1:]).encode(),
            replace=b"dicom-web-filter",
        ),
        media_type="application/dicom+json",
    )


@router.get("/studies", tags=["QIDO-RS"])
async def query_studies(request: Request):
    """This endpoint is used to get all studies mapped to the project.

    Args:
        request (Request): Request object

    Returns:
        response: Response object
    """
    return await retrieve_studies(request=request)


@router.get("/studies/{study}/series", tags=["QIDO-RS"])
async def query_series(study: str, request: Request):
    """This endpoint is used to get all series of a study mapped to the project.

    Args:
        study (str): Study Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """
    return await retrieve_series(study=study, request=request)


@router.get("/studies/{study}/series/{series}/instances", tags=["QIDO-RS"])
async def query_instances(
    study: str,
    series: str,
    request: Request,
):
    """This endpoint is used to get all instances of a series mapped to the project.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """
    return await retrieve_instances(study=study, series=series, request=request)
