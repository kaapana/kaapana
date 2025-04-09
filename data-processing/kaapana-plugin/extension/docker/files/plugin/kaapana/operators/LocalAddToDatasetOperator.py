import json
from pathlib import Path
from typing import List
import requests

from kaapana.blueprints.kaapana_global_variables import (
    SERVICES_NAMESPACE,
)
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.logger import get_logger

logger = get_logger(__name__)


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
                    if self.from_other_project:
                        select_project_from_other_project(
                            series_uid=series_uid, **kwargs
                        )
                    else:
                        clinical_trail_tag = metadata.get(
                            "00120020 ClinicalTrialProtocolID_keyword"
                        )
                        select_project_and_add_dataset(
                            series_uid=series_uid,
                            clinical_trail_tag=clinical_trail_tag,
                            **kwargs,
                        )

    def __init__(
        self,
        dag,
        name: str = "add2dataset",
        tags_to_add_from_file: List[str] = [
            "00120010 ClinicalTrialSponsorName_keyword"
        ],
        from_other_project=False,
        *args,
        **kwargs,
    ):
        """
        :param tags_to_add_from_file: a list of fields form the metadata json which holds the dataset name.
        """

        self.tags_to_add_from_file = tags_to_add_from_file
        self.from_other_project = from_other_project
        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)


def select_project_from_other_project(series_uid: str, **kwargs):
    """
    Select the project from the other project.
    This function is used when the user wants to select a project from the other project.
    """
    config = kwargs["dag_run"].conf
    workflow_form = config.get("workflow_form")
    data_form = config.get("data_form")
    dataset_name = data_form.get("dataset_name", None)
    logger.info(f"Copying {dataset_name=}")
    if dataset_name:
        projects = workflow_form.get("projects")
        for project_name in projects:
            logger.info(
                f"Add {series_uid} to dataset {dataset_name} of project {project_name}"
            )
            project = get_project_by_name(project_name)
            add_identifier_to_dataset_in_project(
                identifiers=[series_uid],
                dataset_name=dataset_name,
                project=project,
            )


def select_project_and_add_dataset(series_uid: str, clinical_trail_tag: str):
    """
    Select the project based on the clinical trial tag and add the series to the dataset.
    Of both the admin project and the project of the clinical trial tag.
    """

    try:
        project = get_project_by_name(
            metadata.get("00120020 ClinicalTrialProtocolID_keyword")
        )
    except:
        project = get_project_by_name("admin")

    admin_project = get_project_by_name("admin")
    # extract datasets from dicom tags
    datasets = [
        metadata.get(dicom_tags)
        for dicom_tags in self.tags_to_add_from_file
        if metadata.get(dicom_tags) is not None
    ]
    assert datasets
    for dataset in datasets:
        add_identifier_to_dataset_in_project(
            identifiers=[series_uid],
            dataset_name=dataset,
            project=project,
        )
        add_identifier_to_dataset_in_project(
            identifiers=[series_uid],
            dataset_name=dataset,
            project=admin_project,
        )


def add_identifier_to_dataset_in_project(
    identifiers: list, dataset_name: str, project: dict
):
    """
    Add a list of series uids as identifiers to the dataset in project via the API of the kaapana-backend.
    """
    project_header = {"Project": json.dumps(project)}
    try:
        res = requests.put(
            f"http://kaapana-backend-service.{SERVICES_NAMESPACE}.svc:5000/client/dataset",
            json=dict(
                action="ADD",
                name=dataset_name,
                identifiers=identifiers,
            ),
            headers=project_header,
        )
        if res.status_code != 200:
            raise Exception(f"ERROR: [{res.status_code}] {res.text}")
    except Exception as e:
        print(f"Processing of {identifiers=} threw an error.", e)
        raise e


def get_project_by_name(project_name: str):
    """
    Return the project object from the access-information-point database with name project_name

    Raises:
        HttpException: If the response from the access-information code has status code >= 400.
    """
    response = requests.get(
        f"http://aii-service.{SERVICES_NAMESPACE}.svc:8080/projects/{project_name}"
    )
    response.raise_for_status()
    return response.json()
