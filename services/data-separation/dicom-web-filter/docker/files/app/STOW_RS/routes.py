import json
import logging
from uuid import UUID

import httpx
from app import config, crud
from app.database import get_session
from app.utils import get_default_project_id
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
    session: AsyncSession,
    request: Request,
    project_id: UUID,
):
    """Map the dicom series to the project. This is done by adding the dicom series to the database and mapping it to the project.

    Args:
        session (AsyncSession): Database session
        request (Request): Request object

    """
    logger.info(
        project_id
    )  # Extract the 'clinical_trial_protocol_info' query parameter
    # This parameter was set in the dcmweb helper
    clinical_trial_protocol_info = json.loads(
        request.query_params.get("clinical_trial_protocol_info")
    )

    for series_instance_uid in clinical_trial_protocol_info:
        # Add the dicom data to the database
        try:
            await crud.add_dicom_data(
                session,
                series_instance_uid=series_instance_uid,
                study_instance_uid=clinical_trial_protocol_info[series_instance_uid][
                    "study_instance_uid"
                ],
                description="Dicom data",
            )
        except IntegrityError as e:
            await session.rollback()
            logger.warning(f"{series_instance_uid=} already exists in the database")

        # Map the dicom data to the project
        try:
            await crud.add_data_project_mapping(
                session,
                series_instance_uid=series_instance_uid,
                project_id=project_id,
            )
        except IntegrityError as e:
            await session.rollback()
            logger.warning(
                f"{series_instance_uid=} already exists in the project mapping"
            )


@router.post("/studies", tags=["STOW-RS"])
async def store_instances(
    request: Request,
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Depends(get_default_project_id),
):
    """This endpoint is used to store data in the DICOMWeb server. The data is being mapped to the project and then streamed to the DICOMWeb server.

    Args:
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        Response: Response object
    """

    await __map_dicom_series_to_project(session, request, project_id)

    await __stream_data(request, url=f"studies")

    return Response(status_code=200)


@router.post("/studies/{study}", tags=["STOW-RS"])
async def store_instances_in_study(
    study: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Depends(get_default_project_id),
):
    """This endpoint is used to store data in the DICOMWeb server. The data is being mapped to the project and then streamed to the DICOMWeb server.

    Args:
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        Response: Response object
    """

    await __map_dicom_series_to_project(session, request, project_id)

    await __stream_data(request, url=f"studies/{study}")

    return Response(status_code=200)
