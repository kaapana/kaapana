import logging
from uuid import UUID

from app.crud import BaseDataAdapter
from app.utils import get_project_data_adapter
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from app.schemas import DataProjectMappings
from typing import List

router = APIRouter()
logger = logging.getLogger(__name__)


# @router.put(
#     "/projects/{project_id}/data/{series_instance_uid}",
#     tags=["DataProjects"],
# )


# @router.get(
#     "/projects/{project_id}/data",
#     tags=["DataProjects"],
#     response_model=DataProjectMappings,
# )


# @router.get(
#     "/data/{series_instance_uid}/projects",
#     tags=["DataProjects"],
#     response_model=List[DataProjectMappings],
# )


# @router.delete(
#     "/projects/{project_id}/data/{series_instance_uid}",
#     tags=["DataProjects"],
# )


# @router.put(
#     "/data/{series_instance_uid}",
#     tags=["DataProjects"],
# )

###### New ROUTES ######


@router.put(
    "/project-mappings", tags=["DataProjects"], response_model=List[DataProjectMappings]
)
async def create_data_project_mapping(
    data_project_mappings: List[DataProjectMappings],
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
):
    """
    Create a DataProjects mapping.
    """
    return await crud.put_data_project_mappings(
        data_project_mappings=data_project_mappings,
    )


@router.get(
    "/project-mappings/",
    tags=["DataProjects"],
    response_model=List[DataProjectMappings],
)
async def get_data_project_mappings(
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    series_instance_uids: List[str] = Query(None),
    study_instance_uids: List[str] = Query(None),
    project_ids: List[UUID] = Query(None),
):
    """
    Get all DataProjects mappings.
    """
    logger.info(f"{series_instance_uids=}")
    logger.info(f"{study_instance_uids=}")
    logger.info(f"{project_ids=}")
    return await crud.get_data_project_mappings(
        series_instance_uids=series_instance_uids,
        study_instance_uids=study_instance_uids,
        project_ids=project_ids,
    )


@router.delete("/project-mappings", tags=["DataProjects"])
async def delete_data_project_mappings(
    data_project_mappings: List[DataProjectMappings],
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
):
    """
    Delete a DataProjects mapping.
    """
    try:
        await crud.delete_data_project_mappings(
            data_project_mappings=data_project_mappings,
        )
    except NameError:
        return Response(
            "One or more DataProjectMappings do not exist!", status_code=404
        )
