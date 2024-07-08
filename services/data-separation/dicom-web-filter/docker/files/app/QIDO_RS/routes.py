from fastapi import APIRouter, Request, Depends, Response
from starlette.status import HTTP_204_NO_CONTENT
from ..proxy_request import proxy_request
from ..database import get_session
from . import crud
from ..config import DICOMWEB_BASE_URL
from sqlalchemy.ext.asyncio import AsyncSession
import json

router = APIRouter()


@router.get("/studies", tags=["QIDO-RS"])
async def query_studies(request: Request, session: AsyncSession = Depends(get_session)):

    # Retrieve studies mapped to the project
    studies = set(await crud.get_all_studies_mapped_to_project(session, 1))

    # check if StudyInstanceUID is in the query parameters
    if "StudyInstanceUID" in request.query_params:
        # Check if the requested studies are mapped to the project
        requested_studies = set(request.query_params.getlist("StudyInstanceUID"))
        studies = studies.intersection(requested_studies)

    if not studies:
        # return empty response with status code 204
        return Response(status_code=HTTP_204_NO_CONTENT)

    # Remove StudyInstanceUID from the query parameters
    query_params = dict(request.query_params)
    query_params["StudyInstanceUID"] = []

    # Add the studies mapped to the project to the query parameters
    for uid in studies:
        query_params["StudyInstanceUID"].append(uid)

    # Update the query parameters
    request._query_params = query_params

    # Send the request to the DICOM Web server
    response = await proxy_request(request, "/studies", "GET")

    # --- Now we will modify the response to replace the DICOM Web URL with the filter URL ---

    # Decode bytes to string and parse JSON
    data_str = response.body.decode("utf-8")
    data_json = json.loads(data_str)

    # Process each item in the JSON data
    for item in data_json:
        if "00081190" in item and "Value" in item["00081190"]:
            original_url = item["00081190"]["Value"][0]

            # TODO: Please refactor this to use a more robust method to replace the URL
            real_dicom_web_routes = "/".join(
                DICOMWEB_BASE_URL.split(":")[-1].split("/")[1:]
            )
            # Replace the real dicom web URL with the filter URL in the response
            # It's basically replacing "dcm4chee-arc/aets/KAAPANA/rs" with "dicom-web-filter"
            item["00081190"]["Value"][0] = original_url.replace(
                real_dicom_web_routes, "dicom-web-filter"
            )

    # Convert JSON back to string and then to bytes
    new_data_str = json.dumps(data_json)
    new_data = new_data_str.encode("utf-8")

    # Update the response body
    response.body = new_data

    return response


@router.get("/studies/{study}/series", tags=["QIDO-RS"])
async def query_series(
    study: str, request: Request, session: AsyncSession = Depends(get_session)
):

    # If StudyInstanceUID is in the query parameters, remove it
    query_params = dict(request.query_params)
    if "StudyInstanceUID" in query_params:
        query_params.pop("StudyInstanceUID")

    # Retrieve series mapped to the project for the given study
    mapped_series_uids = set(
        await crud.get_series_instance_uids_of_study_which_are_mapped_to_project(
            session=session, project_id=1, study_instance_uid=study
        )
    )

    # check if SeriesInstanceUID is in the query parameters
    if "SeriesInstanceUID" in request.query_params:
        # Check if the requested series are mapped to the project
        requested_series = set(request.query_params.getlist("SeriesInstanceUID"))
        mapped_series_uids = mapped_series_uids.intersection(requested_series)

    if not mapped_series_uids:
        return Response(status_code=HTTP_204_NO_CONTENT)

    # Remove SeriesInstanceUID from the query parameters
    query_params["SeriesInstanceUID"] = []

    # Add the series mapped to the project to the query parameters
    for uid in mapped_series_uids:
        query_params["SeriesInstanceUID"].append(uid)

    # Update the query parameters
    request._query_params = query_params

    return await proxy_request(request, f"/studies/{study}/series", "GET")


@router.get("/studies/{study}/series/{series}/instances", tags=["QIDO-RS"])
async def query_instances(study: str, series: str, request: Request):

    # TODO: Only return instances of the series that are mapped to the project (Filtering is on series level)

    return await proxy_request(
        request, f"/studies/{study}/series/{series}/instances", "GET"
    )
