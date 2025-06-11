from typing import List
from uuid import UUID


from .models import DataProjects, DicomData


async def get_all_studies_mapped_to_projects(project_ids: List[UUID]) -> List[str]:
    raise NotImplementedError()


async def get_all_series_mapped_to_projects(project_ids: List[UUID]) -> List[str]:
    raise NotImplementedError()


async def get_series_instance_uids_of_study_which_are_mapped_to_projects(
    project_ids: List[UUID], study_instance_uid: str
) -> List[str]:
    raise NotImplementedError()


async def check_if_series_in_given_study_is_mapped_to_projects(
    project_ids: List[UUID],
    study_instance_uid: str,
    series_instance_uid: str,
) -> bool:
    raise NotImplementedError()


async def add_dicom_data(
    series_instance_uid: str,
    study_instance_uid: str,
    description: str,
) -> DicomData:
    raise NotImplementedError()


async def get_data_of_project(project_id: UUID):
    """
    Return all data that belongs to a project.
    """
    raise NotImplementedError()


async def add_data_project_mapping(
    series_instance_uid: str, project_id: UUID
) -> DataProjects:
    raise NotImplementedError()


async def get_all_series_of_study(study_instance_uid: str) -> List[str]:
    raise NotImplementedError()


async def get_data_project_mapping(session, series_instance_uid: str, project_id: UUID):
    raise NotImplementedError()


async def remove_data_project_mapping(series_instance_uid: str, project_id: UUID):
    """
    Delete a DataProject mapping.
    """
    raise NotImplementedError()


async def series_is_mapped_to_multiple_projects(series_instance_uid: str) -> bool:
    raise NotImplementedError()


async def study_is_mapped_to_multiple_projects(study_instance_uid: str) -> bool:
    raise NotImplementedError()


async def get_project_ids_of_series(series_instance_uid: str):
    """
    Return the ids of all projects that contain series_instance_uid.
    """
    raise NotImplementedError()


async def get_overview() -> dict:
    """
    Return a dictionary with the project_id as key and the series_instance_uids as values
    E.g. {<project_id>: <series_instance_uids> }

    """
    raise NotImplementedError()
