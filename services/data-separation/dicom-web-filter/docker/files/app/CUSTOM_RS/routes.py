import logging
from uuid import UUID

import httpx
from app.crud import BaseDataAdapter
from app.config import DICOMWEB_BASE_URL
from app.utils import get_user_project_ids, get_project_data_adapter
from fastapi import APIRouter, Depends, Path, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.status import HTTP_204_NO_CONTENT

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
    project_id: UUID,
    study: str,
    request: Request,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_ids_of_user=Depends(get_user_project_ids),
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

    if project_id not in project_ids_of_user:
        return Response(status_code=403)

    # Retrieve series mapped to the project for the given study
    mapped_series_uids = (
        await crud.get_series_instance_uids_of_study_which_are_mapped_to_projects(
            project_ids=[project_id], study_instance_uid=study
        )
    )

    logging.info(f"mapped_series_uids: {mapped_series_uids}")

    # get all series of the study
    all_series = await crud.get_all_series_of_study(study_instance_uid=study)

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
            series_instance_uid=series, project_id=project_id
        )

        # Check for other usages
        mapped_project_ids = await crud.get_project_ids_of_series(series)

        if len(mapped_project_ids) == 0:
            # This part should only run if a project deletes the last mapping of a series
            logging.info(f"Finally deleting series: {series}")
            # Delete in PACS
            response = await delete_series_dcm4chee(study, series, request)

    return Response(status_code=200)


@router.delete(
    "/projects/{project_id}/studies/{study}/series/{series}", tags=["Custom"]
)
async def del_series(
    project_id: UUID,
    study: str,
    series: str,
    request: Request,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_ids_of_user=Depends(get_user_project_ids),
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
    if project_id not in project_ids_of_user:
        projects = request.scope.get("token")["projects"]
        logging.info(f"User not in project: {project_id}: {projects=}")
        return Response(status_code=403, content=f"User not in project {project_id}")

    # Check if series is mapped to the project
    if await crud.check_if_series_in_given_study_is_mapped_to_projects(
        project_ids=[project_id],
        study_instance_uid=study,
        series_instance_uid=series,
    ):
        logging.info(f"Deleting series: {series}")

        # Check for other usages
        mapped_project_ids = await crud.get_project_ids_of_series(series)

        # Remove the mapping to the current project
        await crud.remove_data_project_mapping(
            series_instance_uid=series, project_id=project_id
        )

        if len(mapped_project_ids) == 1:
            # This part should only run if a project deletes the last mapping of a series
            logging.info(f"Finally deleting series: {series}")
            # Delete in PACS
            return await delete_series_dcm4chee(study, series, request)
    else:
        return Response(status_code=403, content="Series not mapped to project")


# FOR SLIM VIEWER
@router.get("/series", tags=["Custom"])
async def get_series(
    request: Request,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_ids_of_user=Depends(get_user_project_ids),
):

    if not "StudyInstanceUID" in request.query_params:
        return JSONResponse(
            content={"error": "StudyInstanceUID is required"}, status_code=400
        )

    study = request.query_params["StudyInstanceUID"]

    # Get all series mapped to the project
    series = set(await crud.get_all_series_mapped_to_projects(project_ids_of_user))

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
    study: str,
    request: Request,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_ids_of_user=Depends(get_user_project_ids),
):
    # Get all series mapped to the project
    series = set(await crud.get_all_series_mapped_to_projects(project_ids_of_user))

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
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_ids_of_user=Depends(get_user_project_ids),
):
    if not await crud.check_if_series_in_given_study_is_mapped_to_projects(
        project_ids=project_ids_of_user,
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
