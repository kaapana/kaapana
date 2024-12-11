import httpx
from app.config import DICOMWEB_BASE_URL
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

router = APIRouter()


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
        response = client.post(
            f"{DICOMWEB_BASE_URL}/studies/{study}/reject/113001%5EDCM",
            headers=request.headers,
        )

        if response.status_code != 404:
            response.raise_for_status()

    with httpx.Client() as client:
        response = client.delete(
            f"{DICOMWEB_BASE_URL}/studies/{study}",
            headers=request.headers,
        )

        return Response(content=response.content, status_code=response.status_code)


@router.delete("/studies/{study}/series/{series}", tags=["Custom"])
async def delete_series(study: str, series: str, request: Request):
    """This endpoint is used to delete a series.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """

    with httpx.Client() as client:
        response = client.post(
            f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/reject/113001%5EDCM",
            headers=request.headers,
        )

        if response.status_code != 404:
            response.raise_for_status()

    # Only keep part before "/aets" in DICOMWEB_BASE_URL
    base_url = DICOMWEB_BASE_URL.split("/aets")[0]

    with httpx.Client() as client:
        response = client.delete(
            f"{base_url}/reject/113001%5EDCM",
            headers=request.headers,
        )

        return Response(content=response.content, status_code=response.status_code)


@router.delete("/studies/{study}/series/{series}/instances/{instance}", tags=["Custom"])
async def delete_instance(study: str, series: str, instance: str, request: Request):
    """This endpoint is used to delete an instance.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        instance (str): Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """

    with httpx.Client() as client:
        response = client.post(
            f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}/reject/113001%5EDCM",
            headers=request.headers,
        )

        if response.status_code != 404:
            response.raise_for_status()

    # Only keep part before "/aets" in DICOMWEB_BASE_URL
    base_url = DICOMWEB_BASE_URL.split("/aets")[0]

    with httpx.Client() as client:
        response = client.delete(
            f"{base_url}/reject/113001%5EDCM",
            headers=request.headers,
        )

        return Response(content=response.content, status_code=response.status_code)
