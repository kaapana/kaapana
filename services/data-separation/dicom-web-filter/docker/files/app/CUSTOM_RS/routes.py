from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import httpx
from ..proxy_request import proxy_request
from ..config import DICOMWEB_BASE_URL

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
    return await proxy_request(
        request,
        path=f"/studies/{study}/reject/{codeValue}^{codingSchemeDesignator}",
        method="POST",
    )


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
    return await proxy_request(
        request,
        path=f"/studies/{study}/series/{series}/reject/{codeValue}^{codingSchemeDesignator}",
        method="POST",
    )


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
    return await proxy_request(
        request,
        path=f"/studies/{study}/series/{series}/instances/{instance}/reject/{codeValue}^{codingSchemeDesignator}",
        method="POST",
    )


@router.delete("/studies/{study}", tags=["Custom"])
async def delete_study(study: str, request: Request):
    """This endpoint is used to delete a study.

    Args:
        study (str): Study Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """
    return await proxy_request(request, path=f"/studies/{study}", method="DELETE")


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

    return await proxy_request(
        request,
        path=f"/reject/{codeValue}^{codingSchemeDesignator}",
        method="DELETE",
        base_url=base_url,
    )


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

    return await proxy_request(
        request,
        path=f"/studies/{study}/series",
        method="GET",
        base_url=base_url,
    )


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

    return await proxy_request(
        request,
        path=f"/studies",
        method="GET",
        base_url=base_url,
    )


# get all series
@router.get(
    "/series",
    tags=["Custom"],
)
async def get_series(
    request: Request,
):
    # Query all studies
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://127.0.0.1:8080/studies",
            params=request.query_params,
            headers=request.headers,
        )
        studies = response.json()

    # Get all series of all studies
    series = []

    for study in studies:
        study_instance_uid = study["0020000D"]["Value"][0]
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://127.0.0.1:8080/studies/{study_instance_uid}/series",
                params=request.query_params,
                headers=request.headers,
            )
            # If empty response, continue with next study
            if response.status_code == 204:
                continue
            series += response.json()

    return JSONResponse(content=series, media_type="application/json")