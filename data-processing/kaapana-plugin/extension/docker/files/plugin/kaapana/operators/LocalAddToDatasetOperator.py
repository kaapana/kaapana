import json
from enum import Enum
from pathlib import Path
from typing import List

import requests

from kaapana.blueprints.kaapana_global_variables import (
    SERVICES_NAMESPACE,
)
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalAddToDatasetOperator(KaapanaPythonBaseOperator):
    def start(self, ds, **kwargs):
        print("Start tagging")
        tags = []

        print(f"Tags from form: {tags}")
        run_dir = Path(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = list(Path(run_dir, self.batch_name).glob("*"))

        for batch_element_dir in batch_folder:
            json_files = sorted(
                list(Path(batch_element_dir, self.operator_in_dir).rglob("*.json*"))
            )
            for meta_files in json_files:
                print(f"Do tagging for file {meta_files}")
                with open(meta_files) as fs:
                    metadata = json.load(fs)
                    series_uid = metadata["0020000E SeriesInstanceUID_keyword"]

                    # Adding tags based on other fields of the file
                    file_tags = []

                    for tag_from_file in self.tags_to_add_from_file:
                        value = metadata.get(tag_from_file)
                        if value:
                            file_tags.extend(value)

                    datasets = file_tags
                    for dataset in datasets:
                        try:
                            requests.put(
                                f"http://kaapana-backend-service.{SERVICES_NAMESPACE}.svc:5000/client/dataset",
                                json=dict(
                                    action="ADD",
                                    name=dataset,
                                    identifiers=[series_uid],
                                ),
                            )
                        except Exception as e:
                            print(f"Processing of {series_uid} threw an error.", e)
                            exit(1)

    def __init__(
        self,
        dag,
        name: str = "add2dataset",
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

        self.add_tags_from_file = add_tags_from_file
        self.tags_to_add_from_file = tags_to_add_from_file
        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
