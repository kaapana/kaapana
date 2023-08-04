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
    """
    Operator to assign series to dataset.

    Given the metadata of a series, this operator assigns the series to a dataset based on the tags_to_add_from_file parameter.

    **Inputs:**
    * Metadata of a series
    """

    def start(self, ds, **kwargs):
        print("Start assigning series to dataset")

        run_dir = Path(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = list(Path(run_dir, self.batch_name).glob("*"))

        for batch_element_dir in batch_folder:
            json_files = sorted(
                list(Path(batch_element_dir, self.operator_in_dir).rglob("*.json*"))
            )

            for meta_files in json_files:
                print(f"Do assignment for file {meta_files}")
                with open(meta_files) as fs:
                    metadata = json.load(fs)
                    series_uid = metadata["0020000E SeriesInstanceUID_keyword"]

                    # extract datasets from dicom tags
                    datasets = [
                        tag
                        for dicom_tags in self.tags_to_add_from_file
                        if metadata.get(dicom_tags) is not None
                        for tag in metadata.get(dicom_tags)
                    ]

                    for dataset in datasets:
                        try:
                            res = requests.put(
                                f"http://kaapana-backend-service.{SERVICES_NAMESPACE}.svc:5000/client/dataset",
                                json=dict(
                                    action="ADD",
                                    name=dataset,
                                    identifiers=[series_uid],
                                ),
                            )
                            if res.status_code != 200:
                                raise Exception(
                                    f"ERROR: [{res.status_code}] {res.text}"
                                )
                        except Exception as e:
                            print(f"Processing of {series_uid} threw an error.", e)
                            exit(1)

    def __init__(
        self,
        dag,
        name: str = "add2dataset",
        tags_to_add_from_file: List[str] = ["00120020 ClinicalTrialProtocolID_keyword"],
        *args,
        **kwargs,
    ):
        """
        :param tags_to_add_from_file: a list of fields form the metadata json which holds the dataset name.
        """

        self.tags_to_add_from_file = tags_to_add_from_file
        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
