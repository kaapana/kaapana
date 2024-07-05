from fastapi import APIRouter, Request, Depends
from ..proxy_request import proxy_request
from . import crud
from sqlalchemy.exc import IntegrityError
import json
from ..database import get_session
from .. import config
from sqlalchemy.ext.asyncio import AsyncSession
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


async def map_dicom_series_to_project(session: AsyncSession, request: Request):

    # TODO: Get the external project ID from the request
    # TODO: Check if the external project already exists in the database
    # TODO: If it doesn't exist, create it
    # TODO: If no external project ID is provided safe the data in the default (admin) project

    # Extract the 'clinical_trial_protocol_info' query parameter
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
                project_id=config.DEFAULT_PROJECT_ID,
            )
        except IntegrityError as e:
            await session.rollback()
            logger.warning(
                f"{series_instance_uid=} already exists in the project mapping"
            )


@router.post("/studies", tags=["STOW-RS"])
async def store_instances(
    request: Request, session: AsyncSession = Depends(get_session)
):

    await map_dicom_series_to_project(session, request)

    return await proxy_request(request, "/studies", "POST")


@router.post("/studies/{study}", tags=["STOW-RS"])
async def store_instances_in_study(
    study: str, request: Request, session: AsyncSession = Depends(get_session)
):
    await map_dicom_series_to_project(session, request)

    return await proxy_request(request, f"/studies/{study}", "POST")
