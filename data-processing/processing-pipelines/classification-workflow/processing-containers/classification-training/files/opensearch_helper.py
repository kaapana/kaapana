import os
from typing import List
import logging
from opensearchpy import OpenSearch
from pathlib import Path

# Create a custom logger
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)

c_format = logging.Formatter("%(levelname)s - %(message)s")
c_handler.setFormatter(c_format)

# Add handlers to the logger
logger.addHandler(c_handler)

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
        try:
            patient_uids = []
            from_index = 0
            size = 10
            while True:
                response = os_client.search(
                    index=INDEX,
                    body={
                        "query": {"term": {"00000000 Tags_keyword.keyword": tag}},
                        "from": from_index,
                        "size": size,
                    },
                )
                hits = response["hits"]["hits"]
                patient_uids.extend([hit["_id"] for hit in hits])
                total_hits = response["hits"]["total"]["value"]
                if from_index + size >= total_hits:
                    break
                from_index += size
        except Exception as e:
            logger.error(f"Error while fetching patient UIDs for tag {tag}: {e}")
            exit(1)

        return patient_uids
