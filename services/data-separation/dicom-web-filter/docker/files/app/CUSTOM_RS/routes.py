from fastapi import APIRouter, Request
from ..proxy_request import proxy_request
from ..config import DICOMWEB_BASE_URL

router = APIRouter()


@router.post(
    "/studies/{study}/reject/{codeValue}^{codingSchemeDesignator}", tags=["Custom"]
)
async def reject_study(
    study: str, codeValue: str, codingSchemeDesignator: str, request: Request
):
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
    return await proxy_request(
        request,
        path=f"/studies/{study}/series/{series}/instances/{instance}/reject/{codeValue}^{codingSchemeDesignator}",
        method="POST",
    )


@router.delete("/studies/{study}", tags=["Custom"])
async def delete_study(study: str, request: Request):
    return await proxy_request(request, path=f"/studies/{study}", method="DELETE")


@router.delete("/reject/{codeValue}^{codingSchemeDesignator}", tags=["Custom"])
async def reject(codeValue: str, codingSchemeDesignator: str, request: Request):

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

    # Replace KAAPANA for IOCM_QUALITY in DICOMWEB_BASE_URL
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

    # Replace KAAPANA for IOCM_QUALITY in DICOMWEB_BASE_URL
    base_url = DICOMWEB_BASE_URL.replace("KAAPANA", "IOCM_QUALITY")

    return await proxy_request(
        request,
        path=f"/studies",
        method="GET",
        base_url=base_url,
    )
