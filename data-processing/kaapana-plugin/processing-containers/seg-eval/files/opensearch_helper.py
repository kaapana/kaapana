import os

from kaapanapy.helper import get_opensearch_client, load_workflow_config
from kaapanapy.settings import OpensearchSettings

SERVICES_NAMESPACE = os.environ["SERVICES_NAMESPACE"]
HOST = f"opensearch-service.{SERVICES_NAMESPACE}.svc"
PORT = "9200"
workflow_config = load_workflow_config()
project_form = workflow_config.get("project_form", {})
opensearch_index = project_form.get(
    "opensearch_index", OpensearchSettings().default_index
)

os_client = get_opensearch_client()


def get_ref_series_instance_uid(id: str) -> str:
    ref_obj_old = "00081115 ReferencedSeriesSequence_object_object"
    ref_obj_new = "00081115 ReferencedSeriesSequence_object"
    ref_key = "0020000E SeriesInstanceUID_keyword"
    query_body = {
        "query": {"bool": {"filter": {"term": {"_id": id}}}},
        "_source": [
            f"{ref_obj_old}.{ref_key}",
            f"{ref_obj_new}.{ref_key}",
        ],  # it's enough if one of them exists
    }

    # Exec query
    response = os_client.search(index=opensearch_index, body=query_body)

    hits = response["hits"]["hits"]
    if len(hits) > 1:
        print(
            f"# WARNING: OpenSearch query returned multiple hits for {id=}, using first one"
        )

    hit_src = hits[0]["_source"]
    # check whether the old one or new one is in there
    ref_obj = (
        ref_obj_new
        if ref_obj_new in hit_src
        else ref_obj_old if ref_obj_old in hit_src else None
    )
    # Get ref series UID
    if ref_obj is None:
        raise KeyError(
            f"Neither {ref_obj_old} nor {ref_obj_new} could be found in {hit_src}"
        )
    ref_uid = hit_src[f"{ref_obj}"][f"{ref_key}"]

    return ref_uid
