import os
from typing import List
import logging
from kaapanapy.helper import get_opensearch_client
from kaapanapy.settings import OpensearchSettings

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
INDEX = OpensearchSettings().default_index

os_client = get_opensearch_client()


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
