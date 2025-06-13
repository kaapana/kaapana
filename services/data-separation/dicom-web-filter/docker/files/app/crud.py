from typing import List
from uuid import UUID
import httpx
from app.schemas import DataProjectMappings

from app.config import PROJECT_INFORMATION_SOURCE, DICOMWEB_BASE_URL

if PROJECT_INFORMATION_SOURCE == "POSTGRES":
    import app.crud_postgres as crud
elif PROJECT_INFORMATION_SOURCE == "OPENSEARCH":
    import app.opensearch_adapter.crud_opensearch as crud


class BaseDataAdapter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def get_data_project_mappings(
        self,
        project_ids: List[UUID] = None,
        series_instance_uids: List[str] = None,
        study_instance_uids: List[str] = None,
    ) -> List[DataProjectMappings]:
        """
        Return all DataProjectMappings for a given project.
        """
        return await crud.get_data_project_mappings(
            project_ids=project_ids,
            series_instance_uids=series_instance_uids,
            study_instance_uids=study_instance_uids,
            **self.kwargs,
        )

    async def put_data_project_mappings(
        self,
        data_project_mappings=List[DataProjectMappings],
    ) -> List[DataProjectMappings]:
        """
        Create or update a DataProjectMappings entry.
        """
        return await crud.put_data_project_mappings(
            data_project_mappings=data_project_mappings,
            **self.kwargs,
        )

    async def delete_data_project_mappings(
        self,
        data_project_mappings: List[DataProjectMappings],
    ):
        """
        Delete a DataProjectMappings entry.
        """
        return await crud.delete_data_project_mappings(
            data_project_mappings=data_project_mappings,
            **self.kwargs,
        )

    async def get_all_series_of_study(self, study_instance_uid: str) -> List[str]:
        """
        Return all series_instance_uids of a study stored in the PACS.
        """
        async with httpx.AsyncClient() as client:
            async with client.get(
                "GET", f"{DICOMWEB_BASE_URL}/studies/{study_instance_uid}/series"
            ) as response:
                response.raise_for_status()
                data = response.json()

                return [series.get("0020000E").get("Value")[0] for series in data]
