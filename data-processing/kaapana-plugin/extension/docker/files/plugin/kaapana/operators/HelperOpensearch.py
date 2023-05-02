from typing import List, Dict
from opensearchpy import OpenSearch
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE


class HelperOpensearch:
    study_uid_tag = "0020000D StudyInstanceUID_keyword"
    series_uid_tag = "0020000E SeriesInstanceUID_keyword"
    SOPInstanceUID_tag = "00080018 SOPInstanceUID_keyword"
    modality_tag = "00080060 Modality_keyword"
    protocol_name = "00181030 ProtocolName_keyword"
    curated_modality_tag = "00000000 CuratedModality_keyword"

    host = f"opensearch-service.{SERVICES_NAMESPACE}.svc"
    port = "9200"
    index = "meta-index"
    auth = None
    # auth = ('admin', 'admin') # For testing only. Don't store credentials in code.

    os_client = OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_compress=True,  # enables gzip compression for request bodies
        http_auth=auth,
        # client_cert = client_cert_path,
        # client_key = client_key_path,
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        timeout=2,
        # ca_certs = ca_certs_path
    )

    @staticmethod
    def get_query_dataset(query, index=None, only_uids=False):
        index = index if index is not None else HelperOpensearch.index
        print("Getting dataset for query: {}".format(query))
        print("index: {}".format(index))

        query_dict = {
            "query": query,
            "_source": {
                "includes": [
                    HelperOpensearch.study_uid_tag,
                    HelperOpensearch.series_uid_tag,
                    HelperOpensearch.SOPInstanceUID_tag,
                    HelperOpensearch.modality_tag,
                    HelperOpensearch.protocol_name,
                    HelperOpensearch.curated_modality_tag,
                ]
            },
        }

        try:
            hits = HelperOpensearch.execute_opensearch_query(query_dict)
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
        index="meta-index",
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
    def get_dcm_uid_objects(series_instance_uids):
        res = HelperOpensearch.execute_opensearch_query(
            query={"bool": {"must": [{"ids": {"values": series_instance_uids}}]}},
            index=HelperOpensearch.index,
            source={
                "includes": [
                    HelperOpensearch.study_uid_tag,
                    HelperOpensearch.series_uid_tag,
                    HelperOpensearch.SOPInstanceUID_tag,
                    HelperOpensearch.modality_tag,
                    HelperOpensearch.curated_modality_tag,
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
            exit(1)
