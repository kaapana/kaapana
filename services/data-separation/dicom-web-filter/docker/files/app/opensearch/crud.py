from typing import List
from uuid import UUID
from opensearchpy import OpenSearch

from app.schemas import DataProjectMappings
from app.opensearch.utils import (
    get_project_index_mapping,
)
from kaapanapy.helper.HelperOpensearch import DicomTags
from kaapanapy.logger import get_logger

logger = get_logger(__name__)


async def get_data_project_mappings(
    os_client: OpenSearch,
    project_ids: List[UUID] = None,
    series_instance_uids: List[str] = None,
    study_instance_uids: List[str] = None,
) -> List[DataProjectMappings]:
    """
    Return all DataProjectMappings for a given project.
    """
    project_index_mapping = await get_project_index_mapping()
    index_project_mapping = {v: k for k, v in project_index_mapping.items()}
    if project_ids:
        os_indices = ",".join(
            [project_index_mapping.get(project_id) for project_id in project_ids]
        )
    else:
        os_indices = ",".join(project_index_mapping.values())

    query = {"bool": {"must": []}}
    if series_instance_uids:
        query["bool"]["must"].append(
            {"terms": {DicomTags.series_uid_tag: series_instance_uids}}
        )
    if study_instance_uids:
        query["bool"]["must"].append(
            {"terms": {DicomTags.study_uid_tag: study_instance_uids}}
        )
    else:
        query = {"match_all": {}}

    response = os_client.search(
        index=os_indices,
        body={
            "query": query,
            "_source": [DicomTags.study_uid_tag, DicomTags.series_uid_tag],
        },
    )
    hits = response["hits"]["hits"]
    return [
        DataProjectMappings(
            series_instance_uid=hit.get("_source")[DicomTags.series_uid_tag],
            study_instance_uid=hit.get("_source")[DicomTags.study_uid_tag],
            project_id=index_project_mapping.get(hit.get("_index")),
        )
        for hit in hits
    ]


async def put_data_project_mappings(
    os_client: OpenSearch,
    data_project_mappings: List[DataProjectMappings],
) -> List[DataProjectMappings]:
    """
    Create or update a DataProjectMappings entry.
    """
    logger.error("Creation of DataProjectMappings not supported with mode Opensearch.")
    return []


async def delete_data_project_mappings(
    os_client: OpenSearch,
    data_project_mappings: DataProjectMappings,
):
    """
    Delete a DataProjectMappings entry.
    """
    logger.error("Deletion of DataProjectMappings not supported with mode Opensearch.")
    return
