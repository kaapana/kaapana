from opensearchpy import OpenSearch
import os
from typing import List

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


class OpenSearchHelper:
    @staticmethod
    def get_list_of_uids_of_tag(tag: str) -> List[str]:
        query_body = {
            "query": {"term": {"00000000 Tags_keyword.keyword": tag}},
            "_source": ["_id"],
        }

        # Execute the query
        response = os_client.search(index=INDEX, body=query_body)

        # Extract the patient UIDs from the response
        patient_uids = [hit["_id"] for hit in response["hits"]["hits"]]

        return patient_uids
