from typing import List
from uuid import UUID
from opensearchpy import OpenSearch

from app.schemas import DataProjects, DicomData
from app.opensearch_adapter.utils import get_project_indices, get_project_index
from kaapanapy.helper.HelperOpensearch import DicomTags
from kaapanapy.logger import get_logger

logger = get_logger(__name__)


async def get_all_studies_mapped_to_projects(
    os_client: OpenSearch, project_ids: List[UUID]
) -> List[str]:
    project_indices = await get_project_indices(project_ids)
    response = os_client.search(
        index=",".join(project_indices),
        body={
            "query": {"match_all": {}},
            "_source": [DicomTags.study_uid_tag],
        },
    )
    studies = (
        hit["_source"].get(DicomTags.study_uid_tag) for hit in response["hits"]["hits"]
    )
    return list(set(studies))


async def get_all_series_mapped_to_projects(
    os_client: OpenSearch, project_ids: List[UUID]
) -> List[str]:
    project_indices = await get_project_indices(project_ids)
    response = os_client.search(
        index=",".joins(project_indices),
        body={
            "query": {"match_all": {}},
            "_source": [DicomTags.series_uid_tag],
        },
    )
    series = (
        hit["_source"].get(DicomTags.series_uid_tag) for hit in response["hits"]["hits"]
    )
    return list(set(series))


async def get_series_instance_uids_of_study_which_are_mapped_to_projects(
    os_client: OpenSearch, project_ids: List[UUID], study_instance_uid: str
) -> List[str]:
    """
    Return all series_instance_uids of a study that are mapped to the given projects.
    """
    project_indices = await get_project_indices(project_ids)
    response = os_client.search(
        index=",".join(project_indices),
        body={
            "query": {
                "bool": {
                    "must": [{"match": {DicomTags.study_uid_tag: study_instance_uid}}]
                }
            },
            "_source": [],
        },
    )
    series_instance_uids = (
        hit["_source"][DicomTags.series_uid_tag] for hit in response["hits"]["hits"]
    )
    return list(set(series_instance_uids))


async def check_if_series_in_given_study_is_mapped_to_projects(
    os_client: OpenSearch,
    project_ids: List[UUID],
    study_instance_uid: str,
    series_instance_uid: str,
) -> bool:
    """
    Check if a series_instance_uid in a study is mapped to the given projects.
    """
    project_indices = await get_project_indices(project_ids)
    response = os_client.search(
        index=",".join(project_indices),
        body={
            "query": {
                "bool": {
                    "must": [
                        {"match": {DicomTags.study_uid_tag: study_instance_uid}},
                        {"match": {DicomTags.series_uid_tag: series_instance_uid}},
                    ]
                }
            },
        },
    )
    if response["hits"]["total"]["value"] > 0:
        return True
    return False


async def add_dicom_data(
    series_instance_uid: str,
    study_instance_uid: str,
    description: str,
) -> DicomData:
    logger.warning(
        "This method has no effect. It is required to support the database mode."
    )
    return DicomData(
        series_instance_uid=series_instance_uid,
        study_instance_uid=study_instance_uid,
        description=description,
    )


async def get_data_of_project(os_client: OpenSearch, project_id: UUID):
    """
    Return all data that belongs to a project.
    """
    project_index = await get_project_index(project_id)
    response = os_client.search(
        index=project_index,
        body={
            "query": {"match_all": {}},
            "_source": [
                DicomTags.series_uid_tag,
            ],
        },
    )
    series_instance_uids = [
        hit["_source"][DicomTags.series_uid_tag] for hit in response["hits"]["hits"]
    ]
    return series_instance_uids


async def add_data_project_mapping(
    os_client: OpenSearch, series_instance_uid: str, project_id: UUID
) -> DataProjects:
    logger.warning(
        "This method has no effect. It is required to support the database mode."
    )
    return DataProjects(series_instance_uid=series_instance_uid, project_id=project_id)


async def get_all_series_of_study(
    os_client: OpenSearch, study_instance_uid: str
) -> List[str]:
    response = os_client.search(
        body={
            "query": {"match": {DicomTags.study_uid_tag: study_instance_uid}},
            "_source": [DicomTags.series_uid_tag],
        },
    )
    return [
        hit["_source"][DicomTags.series_uid_tag] for hit in response["hits"]["hits"]
    ]


async def remove_data_project_mapping(
    os_client: OpenSearch, series_instance_uid: str, project_id: UUID
):
    """
    Remove the document correpsonding to the series_instance_uid from the project index.
    """
    try:
        project_index = await get_project_index(project_id)
    except Exception as e:
        logger.error(f"Project index not found for project_id {project_id}: {e}")
        raise NameError(f"Project {project_id} does not exist!")
    os_client.delete_by_query(
        index=project_index,
        body={
            "query": {
                "bool": {
                    "must": [
                        {"match": {DicomTags.series_uid_tag: series_instance_uid}},
                    ]
                }
            }
        },
    )
    return


async def series_is_mapped_to_multiple_projects(
    os_client: OpenSearch, series_instance_uid: str
) -> bool:
    """
    Check if a series_instance_uid is mapped to multiple projects.
    """
    response = os_client.search(
        body={
            "query": {
                "bool": {
                    "must": [{"match": {DicomTags.series_uid_tag: series_instance_uid}}]
                }
            },
            "_source": [DicomTags.series_uid_tag],
        },
    )
    return response["hits"]["total"]["value"] > 1


async def study_is_mapped_to_multiple_projects(
    os_client: OpenSearch, study_instance_uid: str
) -> bool:
    """
    Check if a study_instance_uid is mapped to multiple projects.
    """
    response = os_client.search(
        body={
            "query": {
                "bool": {
                    "must": [{"match": {DicomTags.study_uid_tag: study_instance_uid}}]
                }
            },
            "_source": [DicomTags.study_uid_tag],
        },
    )
    return response["hits"]["total"]["value"] > 1


async def get_project_ids_of_series(
    os_client: OpenSearch, series_instance_uid: str
) -> List[UUID]:
    """
    Return the ids of all projects that contain series_instance_uid.
    """
    response = os_client.search(
        body={
            "query": {
                "bool": {
                    "must": [{"match": {DicomTags.series_uid_tag: series_instance_uid}}]
                }
            },
            "_source": [DicomTags.project_id_tag],
        },
    )
    project_ids = list(
        set([UUID(hit.get("_index")) for hit in response["hits"]["hits"]])
    )

    return get_project_indices(project_ids)
