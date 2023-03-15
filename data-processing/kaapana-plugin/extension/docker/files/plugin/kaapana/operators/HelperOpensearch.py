import os

from opensearchpy import OpenSearch

SERVICES_NAMESPACE = os.getenv("SERVICES_NAMESPACE", None)


class HelperOpensearch:
    study_uid_tag = "0020000D StudyInstanceUID_keyword"
    series_uid_tag = "0020000E SeriesInstanceUID_keyword"
    SOPInstanceUID_tag = "00080018 SOPInstanceUID_keyword"
    modality_tag = "00080060 Modality_keyword"
    protocol_name = "00181030 ProtocolName_keyword"
    curated_modality_tag = "curated_modality"

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
    def get_query_cohort(query, index=None, only_uids=False):
        index = index if index is not None else HelperOpensearch.index
        print("Getting cohort for query: {}".format(query))
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
            # TODO: this is incorrect once we exceed 10000 items per cohort
            res = HelperOpensearch.os_client.search(
                index=[index], body=query_dict, size=10000, from_=0
            )
        except Exception as e:
            print("ERROR in search!")
            print(e)
            return None

        if "hits" in res and "hits" in res["hits"]:
            hits = res["hits"]["hits"]
        else:
            raise ValueError("Invalid OpenSearch query!")

        if only_uids:
            return [hit["_id"] for hit in hits]
        else:
            return hits

    @staticmethod
    def get_dcm_uid_objects(series_instance_uids, index):
        query_dict = {
            "query": {"ids": {"values": series_instance_uids}},
            "_source": {
                "includes": [
                    HelperOpensearch.study_uid_tag,
                    HelperOpensearch.series_uid_tag,
                    HelperOpensearch.SOPInstanceUID_tag,
                    HelperOpensearch.modality_tag,
                    HelperOpensearch.curated_modality_tag,
                ]
            },
        }

        try:
            res = HelperOpensearch.os_client.search(
                # TODO: this is incorrect once we exceed 10000 items per cohort
                index=index,
                body=query_dict,
                size=10000,
                from_=0,
            )
        except Exception as e:
            print(e)
            raise ValueError("ERROR in OpenSearch search!")

        if "hits" in res and "hits" in res["hits"]:
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
                for hit in res["hits"]["hits"]
            ]
        else:
            raise ValueError("Invalid OpenSearch query!")

    @staticmethod
    def get_series_metadata(series_uid, index=None):
        index = index if index is not None else HelperOpensearch.index
        return HelperOpensearch.os_client.get(index=index, id=series_uid)["_source"]

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
