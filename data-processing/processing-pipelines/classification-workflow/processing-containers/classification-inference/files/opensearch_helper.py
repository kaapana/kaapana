import os
from typing import List

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


class OpenSearchHelper:
    @staticmethod
    def add_tag_to_id(doc_id: str, tag: str) -> None:
        # Fetch the current tags of the document
        response = os_client.get(
            index=INDEX, id=doc_id, _source_includes=["00000000 Tags_keyword"]
        )
        current_tags = response["_source"].get("00000000 Tags_keyword", [])

        # Check if the tag is not already in the list
        if tag not in current_tags:
            current_tags.append(tag)
            update_body = {"doc": {"00000000 Tags_keyword": current_tags}}

            # Execute the update
            os_client.update(index=INDEX, id=doc_id, body=update_body)
