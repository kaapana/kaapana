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


class OpenSearchHelper:
    @staticmethod
    def add_tag_to_id(doc_id: str, tag: str) -> None:
        # Fetch the current tags of the document
        response = os_client.get(
            index=opensearch_index, id=doc_id, _source_includes=["00000000 Tags_keyword"]
        )
        current_tags = response["_source"].get("00000000 Tags_keyword", [])

        # Check if the tag is not already in the list
        if tag not in current_tags:
            current_tags.append(tag)
            update_body = {"doc": {"00000000 Tags_keyword": current_tags}}

            # Execute the update
            os_client.update(index=opensearch_index, id=doc_id, body=update_body)
