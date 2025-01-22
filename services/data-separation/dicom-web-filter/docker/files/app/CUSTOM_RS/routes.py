import logging

from app.WADO_RS.routes import get_boundary, stream
import httpx
from app import crud
from app.config import DICOMWEB_BASE_URL
from app.database import get_session
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

# Set logging level
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

router = APIRouter()


async def delete_study_dcm4chee(study: str, request: Request):
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


async def delete_series_dcm4chee(study: str, series: str, request: Request):
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


async def delete_instance_dcm4chee(
    study: str, series: str, instance: str, request: Request
):
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


@router.delete("/projects/{project_id}/studies/{study}", tags=["Custom"])
async def del_study(
    project_id: int,
    study: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    This endpoint is used to delete a study.
    For all series belonging to study the mappings to project will be deleted.
    If the series only belongs to one project, the series will be deleted from the PACS as well.

    Args:
        study (str): Study Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """

    if project_id not in [
        project["id"] for project in request.scope.get("token")["projects"]
    ]:
        return Response(status_code=403)

    # Retrieve series mapped to the project for the given study
    mapped_series_uids = (
        await crud.get_series_instance_uids_of_study_which_are_mapped_to_projects(
            session=session, project_ids=[project_id], study_instance_uid=study
        )
    )

    logging.info(f"mapped_series_uids: {mapped_series_uids}")

    # get all series of the study
    all_series = await crud.get_all_series_of_study(
        session=session, study_instance_uid=study
    )

    logging.info(f"all_series: {all_series}")

    # check if all series of the study are mapped to the project
    if set(mapped_series_uids) == set(all_series):
        logging.info(f"Deleting entire study: {study}")
    else:
        logging.info(f"Deleting only some series of study: {study}")
        logging.info(f"mapped_series_uids: {mapped_series_uids}")

    for series in mapped_series_uids:
        logging.info(f"Deleting series: {series}")
        await crud.remove_data_project_mapping(
            session=session, series_instance_uid=series, project_id=project_id
        )

        # Check for other usages
        mapped_project_ids = await crud.get_project_ids_of_series(session, series)

        if len(mapped_project_ids) == 0:
            # This part should only run if a project deletes the last mapping of a series
            logging.info(f"Finally deleting series: {series}")
            # Delete in PACS
            response = await delete_series_dcm4chee(study, series, request)

    return response


@router.delete(
    "/projects/{project_id}/studies/{study}/series/{series}", tags=["Custom"]
)
async def del_series(
    project_id: int,
    study: str,
    series: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """This endpoint is used to delete a series.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """

    # Check if user is in the project
    if project_id not in [
        project["id"] for project in request.scope.get("token")["projects"]
    ]:
        return Response(status_code=403)

    # Check if series is mapped to the project
    if await crud.check_if_series_in_given_study_is_mapped_to_projects(
        session=session,
        project_ids=[project_id],
        study_instance_uid=study,
        series_instance_uid=series,
    ):
        logging.info(f"Deleting series: {series}")

        # Check for other usages
        mapped_project_ids = await crud.get_project_ids_of_series(session, series)

        # Remove the mapping to the current project
        await crud.remove_data_project_mapping(
            session=session, series_instance_uid=series, project_id=project_id
        )

        if len(mapped_project_ids) == 1:
            # This part should only run if a project deletes the last mapping of a series
            logging.info(f"Finally deleting series: {series}")
            # Delete in PACS
            return await delete_series_dcm4chee(study, series, request)
    else:
        return Response(status_code=403)


@router.get(
    "/studies/{study}/series/{series}/instances/{instance}/bulkdata/{dicomTag}/{itemIndex}/{AttributePath}",
    tags=["Custom"],
)
async def retrieve_instance_bulkdata(
    study: str,
    series: str,
    instance: str,
    dicomTag: str,
    itemIndex: str,
    AttributePath: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    project_ids_of_user = [
        project["id"] for project in request.scope.get("token")["projects"]
    ]

    if request.scope.get(
        "admin"
    ) is True or await crud.check_if_series_in_given_study_is_mapped_to_projects(
        session=session,
        project_ids=project_ids_of_user,
        study_instance_uid=study,
        series_instance_uid=series,
    ):
        boundary = get_boundary()

        return StreamingResponse(
            stream(
                method="GET",
                url=f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}/bulkdata/{dicomTag}/{itemIndex}/{AttributePath}",
                request_headers=request.headers,
                new_boundary=boundary,
            ),
            headers={
                "Transfer-Encoding": "chunked",
                "Content-Type": f"multipart/related; boundary={boundary.decode()}",
            },
        )

    else:
        return Response(status_code=204)
