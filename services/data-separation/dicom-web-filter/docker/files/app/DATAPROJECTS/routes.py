from fastapi import APIRouter, Depends
from fastapi.responses import Response
from app import crud
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import get_session
import logging


router = APIRouter()
logger = logging.getLogger(__name__)


@router.put(
    "/projects/{project_id}/data/{series_instance_uid}",
    tags=["DataProjects"],
)
async def create_data_project_mappings(
    project_id: int,
    series_instance_uid: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Create DataProjects mappings in the database.
    """
    try:
        return await crud.add_data_project_mapping(
            session=session,
            series_instance_uid=series_instance_uid,
            project_id=project_id,
        )

    except IntegrityError:
        return Response("Project mapping already exists!", status_code=200)


@router.get(
    "/projects/{project_id}/data",
    tags=["DataProjects"],
)
async def get_data_by_project_id(
    project_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Return all Data that belong to a project.
    """
    return await crud.get_data_of_project(
        session=session,
        project_id=project_id,
    )


@router.get(
    "/data/{series_instance_uid}/projects",
    tags=["DataProjects"],
)
async def get_projects_by_series_instance_uid(
    series_instance_uid: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get all projects Data belongs to.
    """
    return await crud.get_projects_of_data(
        session=session,
        series_instance_uid=series_instance_uid,
    )


@router.delete(
    "/projects/{project_id}/data/{series_instance_uid}",
    tags=["DataProjects"],
)
async def delete_data_project_mappings(
    project_id: int,
    series_instance_uid: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Delete existing DataProjects mappings from the database.
    """

    try:
        await crud.remove_data_project_mapping(
            session=session,
            series_instance_uid=series_instance_uid,
            project_id=project_id,
        )
    except IntegrityError:
        return Response("Project does not exist!", status_code=404)


@router.put(
    "/data/{series_instance_uid}",
    tags=["DataProjects"],
)
async def create_dicom_data(
    series_instance_uid: str,
    study_uid: str,
    description: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Create DataProjects mappings in the database.
    """
    try:
        return await crud.add_dicom_data(
            session=session,
            series_instance_uid=series_instance_uid,
            study_instance_uid=study_uid,
            description=description,
        )
    except IntegrityError:
        return Response("Dicom data already exists!", status_code=200)
