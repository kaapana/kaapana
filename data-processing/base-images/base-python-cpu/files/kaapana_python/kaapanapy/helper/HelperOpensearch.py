import traceback
from typing import Dict, List

from kaapanapy.helper import get_opensearch_client
from kaapanapy.settings import OpensearchSettings
from kaapanapy.logger import get_logger

logger = get_logger(__name__)


class HelperOpensearch:
    study_uid_tag = "0020000D StudyInstanceUID_keyword"
    series_uid_tag = "0020000E SeriesInstanceUID_keyword"
    SOPInstanceUID_tag = "00080018 SOPInstanceUID_keyword"
    modality_tag = "00080060 Modality_keyword"
    protocol_name = "00181030 ProtocolName_keyword"
    curated_modality_tag = "00000000 CuratedModality_keyword"
    dcmweb_endpoint_tag = "00020026 SourcePresentationAddress_keyword"
    custom_tag = "00000000 Tags_keyword"

    host = f"opensearch-service.{OpensearchSettings().services_namespace}.svc"
    port = "9200"
    index = OpensearchSettings().default_index

    try:
        os_client = get_opensearch_client()
    except Exception as e:
        ### The HelperOpensearch class is imported in the airflow-webserver without correct environment variables.
        ### Hence get_opensearch_client will raise an exception, that we catch here.
        logger.warning(str(e))
        logger.warning(
            f"The os_client cannot be intiliatized without correct environment variables."
        )
        logger.warning(
            "You code may break at another point, because os_client is not defined."
        )

    @staticmethod
    def get_query_dataset(
        query, index=None, only_uids=False, include_custom_tag="", exclude_custom_tag=""
    ):
        index = index if index is not None else HelperOpensearch.index
        print("Getting dataset for query: {}".format(query))
        print("index: {}".format(index))
        includes = [
            HelperOpensearch.study_uid_tag,
            HelperOpensearch.series_uid_tag,
            HelperOpensearch.SOPInstanceUID_tag,
            HelperOpensearch.modality_tag,
            HelperOpensearch.protocol_name,
            HelperOpensearch.curated_modality_tag,
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
            hits = HelperOpensearch.execute_opensearch_query(**query_dict)
        except Exception as e:
            print("ERROR in search!")
            print(e)
            return None

        if only_uids:
            return [hit["_id"] for hit in hits]
        else:
            return hits

    @staticmethod
    def execute_opensearch_query(
        query: Dict = dict(),
        source=dict(),
        index=None,
        sort=[{"0020000E SeriesInstanceUID_keyword.keyword": "desc"}],
        scroll=False,
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

        def _execute_opensearch_query(search_after=None, size=10000) -> List:
            res = HelperOpensearch.os_client.search(
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

    @staticmethod
    def get_dcm_uid_objects(
        series_instance_uids, include_custom_tag="", exclude_custom_tag=""
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

        res = HelperOpensearch.execute_opensearch_query(
            query=query,
            index=HelperOpensearch.index,
            source={
                "includes": [
                    HelperOpensearch.study_uid_tag,
                    HelperOpensearch.series_uid_tag,
                    HelperOpensearch.SOPInstanceUID_tag,
                    HelperOpensearch.modality_tag,
                    HelperOpensearch.curated_modality_tag,
                    HelperOpensearch.dcmweb_endpoint_tag,
                ]
            },
        )

        return [
            {
                "dcm-uid": {
                    "study-uid": hit["_source"][HelperOpensearch.study_uid_tag],
                    "series-uid": hit["_source"][HelperOpensearch.series_uid_tag],
                    "modality": hit["_source"][HelperOpensearch.modality_tag],
                    "curated_modality": hit["_source"][
                        HelperOpensearch.curated_modality_tag
                    ],
                    "source_presentation_address": hit["_source"].get(
                        HelperOpensearch.dcmweb_endpoint_tag
                    ),
                }
            }
            for hit in res
        ]

    @staticmethod
    def get_series_metadata(series_instance_uid, index=None):
        index = index if index is not None else HelperOpensearch.index

        try:
            res = HelperOpensearch.os_client.get(index=index, id=series_instance_uid)
        except Exception as e:
            print("ERROR in search!")
            print(e)
            return None

        return res["_source"]

    @staticmethod
    def delete_by_query(query, index=None):
        index = index if index is not None else HelperOpensearch.index
        try:
            res = HelperOpensearch.os_client.delete_by_query(index=index, body=query)
            print(res)
        except Exception as e:

            print(f"# ERROR deleting from Opensearch: {str(e)}")
            print(f"# query: {query}")
            traceback.print_exc()
            exit(1)
