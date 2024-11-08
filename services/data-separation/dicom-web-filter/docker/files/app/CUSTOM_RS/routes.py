import httpx
from app import crud
from app.config import DEFAULT_PROJECT_ID, DICOMWEB_BASE_URL
from app.database import get_session
from fastapi import APIRouter, Depends, Path, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_204_NO_CONTENT

router = APIRouter()


@router.post(
    "/studies/{study}/reject/{codeValue}^{codingSchemeDesignator}", tags=["Custom"]
)
async def reject_study(
    study: str, codeValue: str, codingSchemeDesignator: str, request: Request
):
    """This endpoint is used to reject a study. Objects in DCM4CHEE can only be deleted, if they are rejected.

    Args:
        study (str): Study Instance UID
        codeValue (str): Code Value of the reason for rejection (e.g. "113001")
        codingSchemeDesignator (str): Coding Scheme Designator of the reason for rejection (e.g. "DCM")
        request (Request): Request object

    Returns:
        response: Response object
    """

    with httpx.Client() as client:
        response = client.post(
            f"{DICOMWEB_BASE_URL}/studies/{study}/reject/{codeValue}%5E{codingSchemeDesignator}",
            headers=request.headers,
        )

        return Response(content=response.content, status_code=response.status_code)


@router.post(
    "/studies/{study}/series/{series}/reject/{codeValue}^{codingSchemeDesignator}",
    tags=["Custom"],
)
async def reject_series(
    study: str,
    series: str,
    codeValue: str,
    codingSchemeDesignator: str,
    request: Request,
):
    """This endpoint is used to reject a series. Objects in DCM4CHEE can only be deleted, if they are rejected.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        codeValue (str): Code Value of the reason for rejection (e.g. "113001")
        codingSchemeDesignator (str): Coding Scheme Designator of the reason for rejection (e.g. "DCM")
        request (Request): Request object

    Returns:
        response: Response object
    """

    with httpx.Client() as client:
        response = client.post(
            f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/reject/{codeValue}%5E{codingSchemeDesignator}",
            headers=request.headers,
        )

        return Response(content=response.content, status_code=response.status_code)


# Currently not used
@router.post(
    "/studies/{study}/series/{series}/instances/{instance}/reject/{codeValue}^{codingSchemeDesignator}",
    tags=["Custom"],
)
async def reject_instance(
    study: str,
    series: str,
    instance: str,
    codeValue: str,
    codingSchemeDesignator: str,
    request: Request,
):
    """This endpoint is used to reject an instance. Objects in DCM4CHEE can only be deleted, if they are rejected.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        instance (str): Instance UID
        codeValue (str): Code Value of the reason for rejection (e.g. "113001")
        codingSchemeDesignator (str): Coding Scheme Designator of the reason for rejection (e.g. "DCM")
        request (Request): Request object

    Returns:
        response: Response object
    """

    with httpx.Client() as client:
        response = client.post(
            f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}/reject/{codeValue}%5E{codingSchemeDesignator}",
            headers=request.headers,
        )

        return Response(content=response.content, status_code=response.status_code)


@router.delete("/studies/{study}", tags=["Custom"])
async def delete_study(study: str, request: Request):
    """This endpoint is used to delete a study.

    Args:
        study (str): Study Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """

    with httpx.Client() as client:
        response = client.delete(
            f"{DICOMWEB_BASE_URL}/studies/{study}",
            headers=request.headers,
        )

        return Response(content=response.content, status_code=response.status_code)


@router.delete("/reject/{codeValue}^{codingSchemeDesignator}", tags=["Custom"])
async def reject(codeValue: str, codingSchemeDesignator: str, request: Request):
    """This endpoint is used to delete objects in DCM4CHEE, which are marked as rejected. We use this endpoint to delete rejected series and instances.

    Args:
        codeValue (str): Code Value of the reason for rejection (e.g. "113001")
        codingSchemeDesignator (str): Coding Scheme Designator of the reason for rejection (e.g. "DCM")
        request (Request): Request object

    Returns:
        response: Response object
    """

    # Only keep part before "/aets" in DICOMWEB_BASE_URL
    base_url = DICOMWEB_BASE_URL.split("/aets")[0]

    with httpx.Client() as client:
        response = client.delete(
            f"{base_url}/reject/{codeValue}%5E{codingSchemeDesignator}",
            headers=request.headers,
        )

        return Response(content=response.content, status_code=response.status_code)


# Only used in dicom web helper to delete series from study
@router.get(
    "/reject/studies/{study}/series",
    tags=["Custom"],
)
async def reject_get_series(
    study: str,
    request: Request,
):
    """This endpoint is used to get all series of a study, which are marked as rejected.

    Args:
        study (str): Study Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """

    # Replace KAAPANA for IOCM_QUALITY in DICOMWEB_BASE_URL
    # TODO: Change this to a more general solution
    base_url = DICOMWEB_BASE_URL.replace("KAAPANA", "IOCM_QUALITY")

    with httpx.Client() as client:
        response = client.get(
            f"{base_url}/studies/{study}/series",
            headers=request.headers,
        )

        return Response(content=response.content, status_code=response.status_code)


# Currently not used
@router.get(
    "/reject/studies",
    tags=["Custom"],
)
async def reject_get_studies(
    request: Request,
):
    """This endpoint is used to get all studies, which are marked as rejected.

    Args:
        request (Request): Request object

    Returns:
        response: Response object
    """

    # Replace KAAPANA for IOCM_QUALITY in DICOMWEB_BASE_URL
    base_url = DICOMWEB_BASE_URL.replace("KAAPANA", "IOCM_QUALITY")

    with httpx.Client() as client:
        response = client.get(
            f"{base_url}/studies",
            headers=request.headers,
        )

        return Response(content=response.content, status_code=response.status_code)


# FOR SLIM VIEWER
@router.get("/series", tags=["Custom"])
async def get_series(request: Request, session: AsyncSession = Depends(get_session)):

    if not "StudyInstanceUID" in request.query_params:
        return JSONResponse(
            content={"error": "StudyInstanceUID is required"}, status_code=400
        )

    study = request.query_params["StudyInstanceUID"]

    # Get all series mapped to the project
    series = set(
        await crud.get_all_series_mapped_to_project(session, DEFAULT_PROJECT_ID)
    )

    # Remove SeriesInstanceUID from the query parameters
    query_params = dict(request.query_params)
    query_params["SeriesInstanceUID"] = []

    # Add the series mapped to the project to the query parameters
    for uid in series:
        query_params["SeriesInstanceUID"].append(uid)

    # Update the query parameters
    request._query_params = query_params

    async def stream_fn(request: Request):
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"{DICOMWEB_BASE_URL}/studies/{study}/series",
                params=request.query_params,
                headers=dict(request.headers),
            ) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(stream_fn(request=request))


# FOR SLIM VIEWER
@router.get("/studies/{study}/instances", tags=["Custom"])
async def get_instances(
    study: str, request: Request, session: AsyncSession = Depends(get_session)
):

    # Get all series mapped to the project
    series = set(
        await crud.get_all_series_mapped_to_project(session, DEFAULT_PROJECT_ID)
    )

    # Remove SeriesInstanceUID from the query parameters
    query_params = dict(request.query_params)
    query_params["SeriesInstanceUID"] = []

    # Add the series mapped to the project to the query parameters
    for uid in series:
        query_params["SeriesInstanceUID"].append(uid)

    # Update the query parameters
    request._query_params = query_params

    async def stream_fn(request: Request):
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"{DICOMWEB_BASE_URL}/studies/{study}/instances",
                params=request.query_params,
                headers=dict(request.headers),
            ) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(stream_fn(request=request))


@router.get(
    "/studies/{study}/series/{series}/instances/{instance}/bulkdata/{tag:path}",
    tags=["Custom"],
)
async def get_bulkdata(
    request: Request,
    study: str,
    series: str,
    instance: str,
    tag: str = Path(...),
    session: AsyncSession = Depends(get_session),
):

    if not await crud.check_if_series_in_given_study_is_mapped_to_project(
        session=session,
        project_id=DEFAULT_PROJECT_ID,
        study_instance_uid=study,
        series_instance_uid=series,
    ) and not request.scope.get("admin"):
        return Response(status_code=HTTP_204_NO_CONTENT)

    async def stream_fn(request: Request):
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}/bulkdata/{tag}",
                params=request.query_params,
                headers=dict(request.headers),
            ) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(stream_fn(request=request))
