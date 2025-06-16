import json
import logging
from uuid import UUID

import httpx
from app import config
from app.crud import BaseDataAdapter, get_project_data_adapter
from app.utils import get_default_project_id
from app.schemas import DataProjectMappings
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

router = APIRouter()
logger = logging.getLogger(__name__)


async def __stream_data(request: Request, url: str = "/studies"):
    """Stream the data to the DICOMWeb server.

    Args:
        request (Request): Request object
        url (str, optional): URL to send the request to. Defaults to "/studies".

    """

    async def data_streamer():
        async for chunk in request.stream():
            yield chunk

    async with httpx.AsyncClient(timeout=500) as client:
        async with client.stream(
            "POST",
            f"{config.DICOMWEB_BASE_URL}/{url}",
            content=data_streamer(),
            headers=dict(request.headers),
        ) as response:
            response.raise_for_status()


async def __map_dicom_series_to_project(
    crud: BaseDataAdapter,
    request: Request,
    project_id: UUID,
):
    """Map the dicom series to the project. This is done by adding the dicom series to the database and mapping it to the project.

    Args:
        request (Request): Request object
        crud (BaseDataAdapter): Data adapter to interact with the database.

    """
    logger.info(
        project_id
    )  # Extract the 'clinical_trial_protocol_info' query parameter
    # This parameter was set in the dcmweb helper
    clinical_trial_protocol_info = json.loads(
        request.query_params.get("clinical_trial_protocol_info")
    )

    for series_instance_uid, ctp_info in clinical_trial_protocol_info.items():
        # Map the dicom data to the project
        await crud.put_data_project_mappings(
            data_project_mappings=[
                DataProjectMappings(
                    series_instance_uid=series_instance_uid,
                    project_id=project_id,
                    study_instance_uid=ctp_info.get("study_instance_uid"),
                )
            ]
        )


@router.post("/studies", tags=["STOW-RS"])
async def store_instances(
    request: Request,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_id: UUID = Depends(get_default_project_id),
):
    """This endpoint is used to store data in the DICOMWeb server. The data is being mapped to the project and then streamed to the DICOMWeb server.

    Args:
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        Response: Response object
    """

    await __map_dicom_series_to_project(
        crud=crud, request=request, project_id=project_id
    )

    await __stream_data(request, url=f"studies")

    return Response(status_code=200)


@router.post("/studies/{study}", tags=["STOW-RS"])
async def store_instances_in_study(
    study: str,
    request: Request,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_id: UUID = Depends(get_default_project_id),
):
    """This endpoint is used to store data in the DICOMWeb server. The data is being mapped to the project and then streamed to the DICOMWeb server.

    Args:
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        Response: Response object
    """

    await __map_dicom_series_to_project(
        crud=crud, request=request, project_id=project_id
    )

    await __stream_data(request, url=f"studies/{study}")

    return Response(status_code=200)
