from app.auth import get_external_session
from app.logger import get_logger
from app.utils import rs_endpoint_url
from fastapi import APIRouter, Request, Response
from starlette.status import HTTP_204_NO_CONTENT

router = APIRouter()

logger = get_logger(__name__)


def retrieve_studies(request: Request) -> Response:
    """Retrieve studies from the DICOM Web server.

    Args:
        request (Request): Request object

    Returns:
        response: Response object
    """
    session = get_external_session(request)
    rs_endpoint = rs_endpoint_url(request)

    headers = {"Accept": "application/dicom+json"}
    response = session.get(f"{rs_endpoint}/studies", headers=headers, timeout=5)
    response.raise_for_status()
    if response.status_code == 204:
        # Return empty response with status code 204
        return Response(status_code=HTTP_204_NO_CONTENT)

    status_code = response.status_code
    response_headers = dict(response.headers)
    content = response.content

    # Prepare response headers
    if "content-encoding" in response_headers:
        del response_headers["content-encoding"]
    if "content-length" in response_headers:
        del response_headers["content-length"]  # Let the server set the content length

    # Construct a new Response object from stored values
    return Response(
        content=content,
        status_code=status_code,
        headers=response_headers,
        media_type=response_headers.get("content-type"),
    )


def retrieve_series(study: str, request: Request) -> Response:
    """Retrieve series from the DICOM Web server.

    Args:
        study (str): Study Instance UID
        request (Request): Request object

    Returns:
        Response: Response object
    """
    session = get_external_session(request)
    rs_endpoint = rs_endpoint_url(request)

    # Send the request to the DICOM Web server
    headers = {"Accept": "application/dicom+json"}
    response = session.get(
        f"{rs_endpoint}/studies/{study}/series", headers=headers, timeout=5
    )
    response.raise_for_status()
    if response.status_code == 204:
        # Return empty response with status code 204
        return Response(status_code=HTTP_204_NO_CONTENT)

    status_code = response.status_code
    response_headers = dict(response.headers)
    content = response.content

    # Prepare response headers
    if "content-encoding" in response_headers:
        del response_headers["content-encoding"]
    if "content-length" in response_headers:
        del response_headers["content-length"]  # Let the server set the content length

    logger.info(content)

    # Construct a new Response object from stored values
    return Response(
        content=content,
        status_code=status_code,
        headers=response_headers,
        media_type=response_headers.get("content-type"),
    )


def retrieve_instances(study: str, series: str, request: Request) -> Response:
    """Retrieve instances from the DICOM Web server.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object

    Returns:
        Response: Response object
    """
    session = get_external_session(request)
    rs_endpoint = rs_endpoint_url(request)
    # Perform a HEAD request to check the response code without retrieving the body

    # Send the request to the DICOM Web server
    headers = {"Accept": "application/dicom+json"}
    response = session.get(
        f"{rs_endpoint}/studies/{study}/series/{series}/instances",
        headers=headers,
        timeout=5,
    )
    response.raise_for_status()
    if response.status_code == 204:
        # Return empty response with status code 204
        return Response(status_code=HTTP_204_NO_CONTENT)

    # Store raw values
    status_code = response.status_code
    response_headers = dict(response.headers)
    content = response.content

    # Prepare response headers
    if "content-encoding" in response_headers:
        del response_headers["content-encoding"]
    if "content-length" in response_headers:
        del response_headers["content-length"]  # Let the server set the content length

    # Construct a new Response object from stored values
    return Response(
        content=content,
        status_code=status_code,
        headers=response_headers,
        media_type=response_headers.get("content-type"),
    )


@router.get("/studies", tags=["QIDO-RS"])
def query_studies(request: Request):
    """This endpoint is used to get all studies mapped to the project.

    Args:
        request (Request): Request object

    Returns:
        response: Response object
    """

    return retrieve_studies(request=request)


@router.get("/studies/{study}/series", tags=["QIDO-RS"])
def query_series(study: str, request: Request):
    """This endpoint is used to get all series of a study mapped to the project.

    Args:
        study (str): Study Instance UID
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        response: Response object
    """

    return retrieve_series(study=study, request=request)


@router.get("/studies/{study}/series/{series}/instances", tags=["QIDO-RS"])
def query_instances(
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
    return retrieve_instances(study=study, series=series, request=request)
