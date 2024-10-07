from typing import Dict, List

from kaapanapy.helper import get_opensearch_client
from kaapanapy.logger import get_logger

logger = get_logger(__name__)


class DicomTags:
    study_uid_tag = "0020000D StudyInstanceUID_keyword"
    series_uid_tag = "0020000E SeriesInstanceUID_keyword"
    SOPInstanceUID_tag = "00080018 SOPInstanceUID_keyword"
    modality_tag = "00080060 Modality_keyword"
    protocol_name = "00181030 ProtocolName_keyword"
    curated_modality_tag = "00000000 CuratedModality_keyword"
    dcmweb_endpoint_tag = "00020026 SourcePresentationAddress_keyword"
    custom_tag = "00000000 Tags_keyword"
    clinical_trial_protocol_id_tag = "00120020 ClinicalTrialProtocolID_keyword"

    is_series_complete_tag = "00000000 IsSeriesComplete_boolean"
    min_instance_number_tag = "00000000 MinInstanceNumber_integer"
    max_instance_number_tag = "00000000 MaxInstanceNumber_integer"
    thumbnail_instance_uid_tag = "00000000 ThumbnailInstanceUID_keyword"
    missing_instance_numbers_tag = "00000000 MissingInstanceNumbers_integer"

class HelperOpensearch:
    def __init__(self):
        self.os_client = get_opensearch_client()

    def get_query_dataset(
        query,
        index=None,
        only_uids=False,
        include_custom_tag="",
        exclude_custom_tag="",
        access_token=None,
    ):
        index = index if index is not None else HelperOpensearch.index
        logger.info("Getting dataset for query: {}".format(query))
        logger.info("index: {}".format(index))
        includes = [
            DicomTags.study_uid_tag,
            DicomTags.series_uid_tag,
            DicomTags.SOPInstanceUID_tag,
            DicomTags.modality_tag,
            DicomTags.protocol_name,
            DicomTags.curated_modality_tag,
        ]
        if include_custom_tag != "":
            includes.append(include_custom_tag)
        excludes = []
        if exclude_custom_tag != "":
            excludes.append(exclude_custom_tag)

        query_dict = {
            "query": query,
            "source": {"includes": includes},
        }

        try:
            hits = HelperOpensearch.execute_opensearch_query(
                **query_dict, access_token=access_token
            )
        except Exception as e:
            logger.error(
                f"Couldn't get query: {query} in index: {index}"
            )
            logger.error(e)
            logger.error(traceback.format_exc())
            return None

        if only_uids:
            return [hit["_id"] for hit in hits]
        else:
            return hits

    def execute_opensearch_query(
        self,
        index,
        query: Dict = dict(),
        source=dict(),
        sort=[{"0020000E SeriesInstanceUID_keyword.keyword": "desc"}],
        scroll=False,
        access_token=None,
    ) -> List:
        """
        TODO: This is currently a duplicate to kaapana-backend/docker/files/app/datasets/utils.py
        Since Opensearch has a strict size limit of 10000 but sometimes scrolling or
        pagination is not desirable, this helper function aggregates paginated results
        into a single one.

        Caution: Removing or adding entries between requests will lead to inconsistencies.
        Opensearch offers the 'scroll' functionality which prevents this, but creating
        the required sessions takes too much time for most requests.
        Therefore, it is not implemented yet

        :param query: query to execute
        :param source: opensearch _source parameter
        :param index: index on which to execute the query
        :param sort: TODO
        :param scroll: use scrolling or pagination -> scrolling currently not impelmented
        :return: aggregated search results
        """
        index = index or HelperOpensearch.index
        os_client = HelperOpensearch._get_client_with_token(access_token)

        def _execute_opensearch_query(search_after=None, size=10000) -> List:
            if not os_client:
                raise Exception("os_client is not initialized.")
            res = os_client.search(
                body={
                    "query": query,
                    "size": size,
                    "_source": source,
                    "sort": sort,
                    **({"search_after": search_after} if search_after else {}),
                },
                index=index,
            )
            if len(res["hits"]["hits"]) > 0:
                return [
                    *res["hits"]["hits"],
                    *_execute_opensearch_query(res["hits"]["hits"][-1]["sort"], size),
                ]
            else:
                return res["hits"]["hits"]

        return _execute_opensearch_query()

    def get_dcm_uid_objects(
        series_instance_uids,
        include_custom_tag="",
        exclude_custom_tag="",
        access_token=None,
    ):
        # default query for fetching via identifiers
        query = {"bool": {"must": [{"ids": {"values": series_instance_uids}}]}}

        # must have custom tag
        if include_custom_tag != "":
            query["bool"]["must"].append(
                {"term": {"00000000 Tags_keyword.keyword": include_custom_tag}}
            )

        # must_not have custom tag
        if exclude_custom_tag != "":
            if "must_not" in query["bool"]:
                query["bool"]["must_not"].append(
                    {"term": {"00000000 Tags_keyword.keyword": exclude_custom_tag}}
                )
            else:
                query["bool"]["must_not"] = [
                    {"term": {"00000000 Tags_keyword.keyword": exclude_custom_tag}}
                ]

        res = self.execute_opensearch_query(
            query=query,
            index=index,
            source={
                "includes": [
                    DicomTags.study_uid_tag,
                    DicomTags.series_uid_tag,
                    DicomTags.SOPInstanceUID_tag,
                    DicomTags.modality_tag,
                    DicomTags.curated_modality_tag,
                    DicomTags.dcmweb_endpoint_tag,
                ]
            },
            access_token=access_token,
        )

        return [
            {
                "dcm-uid": {
                    "study-uid": hit["_source"][DicomTags.study_uid_tag],
                    "series-uid": hit["_source"][DicomTags.series_uid_tag],
                    "modality": hit["_source"][DicomTags.modality_tag],
                    "curated_modality": hit["_source"][DicomTags.curated_modality_tag],
                    "source_presentation_address": hit["_source"].get(
                        DicomTags.dcmweb_endpoint_tag
                    ),
                }
            }
            for hit in res
        ]

    @staticmethod
    def get_series_metadata(series_instance_uid, index=None, access_token=None):
        index = index if index is not None else HelperOpensearch.index
        os_client = HelperOpensearch._get_client_with_token(access_token)
        try:
            res = os_client.get(index=index, id=series_instance_uid)
        except Exception as e:
            logger.error(
                f"Couldn't search series_instance_uid: {series_instance_uid} in index: {index}"
            )
            logger.error(e)
            logger.error(traceback.format_exc())
            return None

        return res["_source"]

    @staticmethod
    def delete_by_query(query, index=None, access_token=None):
        index = index if index is not None else HelperOpensearch.index
        os_client = HelperOpensearch._get_client_with_token(access_token)
        try:
            res = os_client.delete_by_query(index=index, body=query)
            logger.info(res)
        except Exception as e:
            logger.error(f"Couldn't delete query: {query} in index: {index}")
            logger.error(e)
            logger.error(traceback.format_exc())
            exit(1)
