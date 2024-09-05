import os

import requests

OPENSEARCH_URL = os.getenv("OPENSEARCH_URL")
OPENSEARCH_USERNAME = os.getenv("OPENSEARCH_USERNAME")
OPENSEARCH_PASSWORD = os.getenv("OPENSEARCH_PASSWORD")


def query_opensearch(study_uid):
    query = {"query": {"match": {"studyUID": study_uid}}}
    response = requests.post(
        f"{OPENSEARCH_URL}/dicom/_search",
        json=query,
        auth=(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD),
    )
    response.raise_for_status()
    hits = response.json()["hits"]["hits"]
    if hits:
        return hits[0]["_source"]["customTag"]
    return None
