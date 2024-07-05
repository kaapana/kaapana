from fastapi import APIRouter, Request
from ..proxy_request import proxy_request

router = APIRouter()

# WADO-RS routes


@router.get("/studies/{study}", tags=["WADO-RS"])
async def retrieve_study(study: str, request: Request):

    # TODO: Check if all series of the study are mapped to the project
    # TODO: If not, return only the series that are mapped to the project

    return await proxy_request(request, f"/studies/{study}", "GET")


@router.get("/studies/{study}/series/{series}", tags=["WADO-RS"])
async def retrieve_series(study: str, series: str, request: Request):

    # TODO: Check if the series is mapped to the project

    return await proxy_request(request, f"/studies/{study}/series/{series}", "GET")


@router.get("/studies/{study}/series/{series}/instances/{instance}", tags=["WADO-RS"])
async def retrieve_instance(study: str, series: str, instance: str, request: Request):

    # TODO: Check if the series is mapped to the project (Filtering is on series level)

    return await proxy_request(
        request, f"/studies/{study}/series/{series}/instances/{instance}", "GET"
    )


@router.get(
    "/studies/{study}/series/{series}/instances/{instance}/frames/{frames}",
    tags=["WADO-RS"],
)
async def retrieve_frames(
    study: str, series: str, instance: str, frames: str, request: Request
):

    # TODO: Check if the series is mapped to the project (Filtering is on series level)

    return await proxy_request(
        request,
        f"/studies/{study}/series/{series}/instances/{instance}/frames/{frames}",
        "GET",
    )


# TODO: Implement the bulk data retrieval
# @router.get("/{bulkdataReferenceURI}", tags=["WADO-RS"])
# async def retrieve_bulk_data(bulkdataReferenceURI: str, request: Request):
#     print(f"bulkdataReferenceURI: {bulkdataReferenceURI}")
#     return await proxy_request(request, f"/{bulkdataReferenceURI}", "GET")


# Routes for retrieve modifiers


@router.get("/studies/{study}/metadata", tags=["WADO-RS"])
async def retrieve_study_metadata(study: str, request: Request):

    # TODO: Check if all series of the study are mapped to the project
    # TODO: If not, return only the metadata of the series that are mapped to the project

    return await proxy_request(request, f"/studies/{study}/metadata", "GET")


@router.get("/studies/{study}/series/{series}/metadata", tags=["WADO-RS"])
async def retrieve_series_metadata(study: str, series: str, request: Request):

    # TODO: Check if the series is mapped to the project

    return await proxy_request(
        request, f"/studies/{study}/series/{series}/metadata", "GET"
    )


@router.get(
    "/studies/{study}/series/{series}/instances/{instance}/metadata", tags=["WADO-RS"]
)
async def retrieve_instance_metadata(
    study: str, series: str, instance: str, request: Request
):
    
    # TODO: Check if the series is mapped to the project (Filtering is on series level)

    return await proxy_request(
        request,
        f"/studies/{study}/series/{series}/instances/{instance}/metadata",
        "GET",
    )


@router.get("/studies/{study}/rendered", tags=["WADO-RS"])
async def retrieve_study_rendered(study: str, request: Request):

    # TODO: Check if all series of the study are mapped to the project
    # TODO: If not, return only the rendered series that are mapped to the project

    return await proxy_request(request, f"/studies/{study}/rendered", "GET")


@router.get("/studies/{study}/series/{series}/rendered", tags=["WADO-RS"])
async def retrieve_series_rendered(study: str, series: str, request: Request):

    # TODO: Check if the series is mapped to the project

    return await proxy_request(
        request, f"/studies/{study}/series/{series}/rendered", "GET"
    )


@router.get(
    "/studies/{study}/series/{series}/instances/{instance}/rendered", tags=["WADO-RS"]
)
async def retrieve_instance_rendered(
    study: str, series: str, instance: str, request: Request
):
    
    # TODO: Check if the series is mapped to the project (Filtering is on series level)

    return await proxy_request(
        request,
        f"/studies/{study}/series/{series}/instances/{instance}/rendered",
        "GET",
    )
