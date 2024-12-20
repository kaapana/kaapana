import os
import json
import glob
from enum import Enum
from typing import List
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.helper import get_opensearch_client
from kaapanapy.settings import OpensearchSettings
from kaapanapy.logger import get_logger

logger = get_logger(__name__)


class LocalTaggingOperator(KaapanaPythonBaseOperator):
    def __init__(
        self,
        dag,
        tag_field: str = "00000000 Tags_keyword",
        name: str = "tagging",
        add_tags_from_file: bool = False,
        tags_to_add_from_file: List[str] = ["00120020 ClinicalTrialProtocolID_keyword"],
        opensearch_index=None,
        *args,
        **kwargs,
    ):
        """
        Update the tag_field of the series metadata stored in opensearch.
        The values to use for updating the tag_field are provided as a comma-separated string of values by kwargs["dag_run"].conf["form_data"]["tags"].
        The operator supports the actions "add", "delete" and "add_from_file".
        The action is provided by kwargs["dag_run"].conf["form_data"]["action"].


        :param tag_field: The field of the opensearch object where the tags are stored
        :param add_tags_from_file: Determines if the content of the fields specified by tags_to_add_from_file are added as tags
        :param tags_to_add_from_file: A list of fields form the input json where the values are added as tags if add_tags_from_file is true
        :param opensearch_index: Specify the index in opensearch, where the metadata should be updated. If not set derive the index from the project_form in the workflow configuration. If project_form not available use the default opensearch index.
        """

        self.tag_field = tag_field
        self.add_tags_from_file = add_tags_from_file
        self.tags_to_add_from_file = tags_to_add_from_file
        self.opensearch_index = opensearch_index

        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)

    class Action(Enum):
        ADD = "add"
        DELETE = "delete"
        ADD_FROM_FILE = "add_from_file"

    def tagging(
        self,
        series_instance_uid: str,
        tags: List[str],
        tags2add: List[str] = [],
        tags2delete: List[str] = [],
    ):
        logger.info(
            f"Update tags for {series_instance_uid=} in {self.opensearch_index=}"
        )
        logger.info(f"Tags 2 add: {tags2add}")
        logger.info(f"Tags 2 delete: {tags2delete}")

        # Read Tags
        doc = self.os_client.get(index=self.opensearch_index, id=series_instance_uid)
        logger.info(doc)
        index_tags = doc["_source"].get(self.tag_field, [])

        final_tags = list(
            set(tags)
            .union(set(index_tags))
            .difference(set(tags2delete))
            .union(set(tags2add))
        )
        logger.info(f"Final tags: {final_tags}")

        # Write Tags back
        body = {"doc": {self.tag_field: final_tags}}
        self.os_client.update(
            index=self.opensearch_index, id=series_instance_uid, body=body
        )

    def start(self, ds, **kwargs):
        logger.info("Start tagging")
        tags = []
        action = self.Action.ADD_FROM_FILE
        conf = kwargs["dag_run"].conf
        self.os_client = get_opensearch_client()
        if self.opensearch_index:
            pass
        elif project_form := conf.get("project_form"):
            self.opensearch_index = project_form.get("opensearch_index")
        else:
            self.opensearch_index = OpensearchSettings().default_index

        if "form_data" in conf:
            form_data = conf["form_data"]
            if "tags" in form_data:
                tags = form_data["tags"].split(",")
            if "action" in form_data:
                action_param = form_data["action"].lower().strip()
                action = self.Action(action_param)

        logger.info(f"Action: {action}")
        logger.info(f"Tags from form: {tags}")
        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = [
            f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))
        ]

        for batch_element_dir in batch_folder:
            json_files = sorted(
                glob.glob(
                    os.path.join(batch_element_dir, self.operator_in_dir, "*.json*"),
                    recursive=True,
                )
            )
            for meta_files in json_files:
                logger.info(f"Do tagging for file {meta_files}")
                with open(meta_files) as fs:
                    metadata = json.load(fs)
                    series_uid = metadata["0020000E SeriesInstanceUID_keyword"]
                    existing_tags = metadata.get(self.tag_field, [])

                    # Adding tags based on other fields of the file
                    file_tags = []
                    if self.add_tags_from_file:
                        for tag_from_file in self.tags_to_add_from_file:
                            value = metadata.get(tag_from_file)
                            if value:
                                file_tags.extend(value)

                    if action == self.Action.ADD_FROM_FILE:
                        self.tagging(
                            series_uid,
                            tags=existing_tags,
                            tags2add=file_tags,
                        )
                    elif action == self.Action.ADD:
                        self.tagging(
                            series_uid,
                            tags=existing_tags,
                            tags2add=tags,
                        )
                    elif action == self.Action.DELETE:
                        self.tagging(
                            series_uid,
                            tags=existing_tags,
                            tags2delete=tags,
                        )
