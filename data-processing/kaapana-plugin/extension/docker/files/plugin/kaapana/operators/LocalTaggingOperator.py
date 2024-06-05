import os
import json
import glob
from kaapanapy.Clients.OpensearchHelper import KaapanaOpensearchHelper
from kaapanapy.logger import get_logger

from enum import Enum
from typing import List
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

logger = get_logger(__file__)


class LocalTaggingOperator(KaapanaPythonBaseOperator):
    class Action(Enum):
        ADD = "add"
        DELETE = "delete"
        ADD_FROM_FILE = "add_from_file"

    def start(self, ds, **kwargs):
        os_client = KaapanaOpensearchHelper()
        logger.info("Start tagging")
        tags = []
        action = self.Action.ADD_FROM_FILE

        conf = kwargs["dag_run"].conf

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
                        os_client.tagging(
                            series_uid, tags=existing_tags, tags2add=file_tags
                        )
                    elif action == self.Action.ADD:
                        os_client.tagging(series_uid, tags=existing_tags, tags2add=tags)
                    elif action == self.Action.DELETE:
                        os_client.tagging(
                            series_uid, tags=existing_tags, tags2delete=tags
                        )

    def __init__(
        self,
        dag,
        tag_field: str = "00000000 Tags_keyword",
        name: str = "tagging",
        add_tags_from_file: bool = False,
        tags_to_add_from_file: List[str] = ["00120020 ClinicalTrialProtocolID_keyword"],
        *args,
        **kwargs,
    ):
        """
        :param tag_field: the field of the opensearch object where the tags are stored
        :param add_tags_from_file: determines if the content of the fields specified by tags_to_add_from_file are added as tags
        :param tags_to_add_from_file: a list of fields form the input json where the values are added as tags if add_tags_from_file is true
        """

        self.tag_field = tag_field
        self.add_tags_from_file = add_tags_from_file
        self.tags_to_add_from_file = tags_to_add_from_file

        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
