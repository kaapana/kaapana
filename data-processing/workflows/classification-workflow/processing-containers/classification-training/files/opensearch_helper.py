import logging
import os
from typing import List

import requests
from kaapana_client.helper import get_opensearch_client
from kaapana_client.settings import ServicesSettings

# Create a custom logger
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)

c_format = logging.Formatter("%(levelname)s - %(message)s")
c_handler.setFormatter(c_format)

# Add handlers to the logger
logger.addHandler(c_handler)


def get_project_index() -> str:
    # Each project keeps its metadata in its own index. The default index of the platform belongs to the admin
    # project, so the index is taken from the project that started the run.
    identifier = os.environ["KAAPANA_PROJECT_IDENTIFIER"]
    if not identifier:
        raise ValueError("KAAPANA_PROJECT_IDENTIFIER is empty. The task must run in the context of a project.")
    response = requests.get(f"{ServicesSettings().aii_url}/projects/{identifier}")
    response.raise_for_status()
    return response.json()["opensearch_index"]


opensearch_index = get_project_index()
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
                    index=opensearch_index,
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
