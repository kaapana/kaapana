import os

from opensearchpy import OpenSearch

SERVICES_NAMESPACE = os.environ["SERVICES_NAMESPACE"]
HOST = f"opensearch-service.{SERVICES_NAMESPACE}.svc"
PORT = "9200"
INDEX = "meta-index"

os_client = OpenSearch(
    hosts=[{"host": HOST, "port": PORT}],
    http_auth=None,
    use_ssl=False,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
    timeout=2,
)


def get_ref_series_instance_uid(id: str) -> str:
    query_body = {
        "query": {"bool": {"filter": {"term": {"_id": id}}}},
        "_source": [
            "00081115 ReferencedSeriesSequence_object_object.0020000E SeriesInstanceUID_keyword"
        ],
    }

    # Exec query
    response = os_client.search(index=INDEX, body=query_body)

    hits = response["hits"]["hits"]
    if len(hits) > 1:
        print(
            f"# WARNING: OpenSearch query returned multiple hits for {id=}, using first one"
        )

    # Get ref series UID
    ref_uid = hits[0]["_source"]["00081115 ReferencedSeriesSequence_object_object"][
        "0020000E SeriesInstanceUID_keyword"
    ]

    return ref_uid
