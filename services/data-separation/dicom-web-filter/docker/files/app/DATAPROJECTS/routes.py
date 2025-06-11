import logging
from uuid import UUID

from app.crud import BaseDataAdapter
from app.utils import get_project_data_adapter
from fastapi import APIRouter, Depends
from fastapi.responses import Response

router = APIRouter()
logger = logging.getLogger(__name__)


@router.put(
    "/projects/{project_id}/data/{series_instance_uid}",
    tags=["DataProjects"],
)
async def create_data_project_mappings(
    project_id: UUID,
    series_instance_uid: str,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
):
    """
    Create DataProjects mappings in the database.
    """
    return await crud.add_data_project_mapping(
        series_instance_uid=series_instance_uid,
        project_id=project_id,
    )


@router.get(
    "/projects/{project_id}/data",
    tags=["DataProjects"],
)
async def get_data_by_project_id(
    project_id: UUID,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
):
    """
    Return all Data that belong to a project.
    """
    return await crud.get_data_of_project(
        project_id=project_id,
    )


@router.get(
    "/data/{series_instance_uid}/projects",
    tags=["DataProjects"],
)
async def get_projects_by_series_instance_uid(
    series_instance_uid: str,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
):
    """
    Get all projects Data belongs to.
    """
    return await crud.get_project_ids_of_series(
        series_instance_uid=series_instance_uid,
    )


@router.delete(
    "/projects/{project_id}/data/{series_instance_uid}",
    tags=["DataProjects"],
)
async def delete_data_project_mappings(
    project_id: UUID,
    series_instance_uid: str,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
):
    """
    Delete existing DataProjects mappings from the database.
    """
    try:
        await crud.remove_data_project_mapping(
            series_instance_uid=series_instance_uid,
            project_id=project_id,
        )
    except NameError:
        return Response("Project does not exist!", status_code=404)


@router.put(
    "/data/{series_instance_uid}",
    tags=["DataProjects"],
)
async def create_dicom_data(
    series_instance_uid: str,
    study_uid: str,
    description: str,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
):
    """
    Create DataProjects mappings in the database.
    """
    return await crud.add_dicom_data(
        series_instance_uid=series_instance_uid,
        study_instance_uid=study_uid,
        description=description,
    )
