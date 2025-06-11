from typing import List
from uuid import UUID

from app.config import PROJECT_INFORMATION_SOURCE

if PROJECT_INFORMATION_SOURCE == "POSTGRES":
    import app.crud_postgres as crud
    from app.models import DataProjects, DicomData
elif PROJECT_INFORMATION_SOURCE == "OPENSEARCH":
    import crud_opensearch as crud


class BaseDataAdapter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def get_all_studies_mapped_to_projects(
        self, project_ids: List[UUID]
    ) -> List[str]:
        return await crud.get_all_studies_mapped_to_projects(
            project_ids=project_ids, **self.kwargs
        )

    async def get_all_series_mapped_to_projects(
        self, project_ids: List[UUID]
    ) -> List[str]:
        return await crud.get_all_series_mapped_to_projects(
            project_ids=project_ids, **self.kwargs
        )

    async def get_series_instance_uids_of_study_which_are_mapped_to_projects(
        self, project_ids: List[UUID], study_instance_uid: str
    ) -> List[str]:
        return (
            await crud.get_series_instance_uids_of_study_which_are_mapped_to_projects(
                project_ids=project_ids,
                study_instance_uid=study_instance_uid,
                **self.kwargs
            )
        )

    async def check_if_series_in_given_study_is_mapped_to_projects(
        self,
        project_ids: List[UUID],
        study_instance_uid: str,
        series_instance_uid: str,
    ) -> bool:
        return await crud.check_if_series_in_given_study_is_mapped_to_projects(
            project_ids=project_ids,
            study_instance_uid=study_instance_uid,
            series_instance_uid=series_instance_uid,
            **self.kwargs
        )

    async def add_dicom_data(
        self,
        series_instance_uid: str,
        study_instance_uid: str,
        description: str,
    ) -> DicomData:
        return await crud.add_dicom_data(
            self,
            series_instance_uid=series_instance_uid,
            study_instance_uid=study_instance_uid,
            description=description,
            **self.kwargs
        )

    async def get_data_of_project(self, project_id: UUID):
        """
        Return all data that belongs to a project.
        """
        return await crud.get_data_of_project(project_id=project_id, **self.kwargs)

    async def add_data_project_mapping(
        self, series_instance_uid: str, project_id: UUID
    ) -> DataProjects:
        return await crud.add_data_project_mapping(
            series_instance_uid=series_instance_uid,
            project_id=project_id,
            **self.kwargs
        )

    async def get_all_series_of_study(self, study_instance_uid: str) -> List[str]:
        return await crud.get_all_series_of_study(
            study_instance_uid=study_instance_uid, **self.kwargs
        )

    async def get_data_project_mapping(
        self, series_instance_uid: str, project_id: UUID
    ):
        return await crud.get_data_project_mapping(
            series_instance_uid=series_instance_uid,
            project_id=project_id,
            **self.kwargs
        )

    async def remove_data_project_mapping(
        self, series_instance_uid: str, project_id: UUID
    ):
        """
        Delete a DataProject mapping.
        """
        return await crud.remove_data_project_mapping(
            series_instance_uid=series_instance_uid,
            project_id=project_id,
            **self.kwargs
        )

    async def series_is_mapped_to_multiple_projects(
        self, series_instance_uid: str
    ) -> bool:
        return await crud.series_is_mapped_to_multiple_projects(
            series_instance_uid=series_instance_uid, **self.kwargs
        )

    async def study_is_mapped_to_multiple_projects(
        self, study_instance_uid: str
    ) -> bool:
        return await crud.study_is_mapped_to_multiple_projects(
            study_instance_uid=study_instance_uid, **self.kwargs
        )

    async def get_project_ids_of_series(self, series_instance_uid: str):
        """
        Return the ids of all projects that contain series_instance_uid.
        """
        return await crud.get_project_ids_of_series(
            series_instance_uid=series_instance_uid, **self.kwargs
        )

    async def get_overview(self) -> dict:
        """
        Return a dictionary with the project_id as key and the series_instance_uids as values
        E.g. {<project_id>: <series_instance_uids> }

        """
        return await crud.get_overview(**self.kwargs)
