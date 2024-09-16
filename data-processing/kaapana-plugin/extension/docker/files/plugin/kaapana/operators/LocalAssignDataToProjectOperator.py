import os

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
import glob
import pydicom
import json
import requests


class LocalAssignDataToProjectOperator(KaapanaPythonBaseOperator):
    """
    Operator to assign data to projects in Kaapana.

    This operator collects DICOM series data from a specified directory and assigns it to one or more projects in Kaapana.
    The data is sent to the Access Information Interface (AII) API to be assigned to the projects.

    :param dag: The DAG object associated with the operator.
    :param projects: A list of project names to assign the data to.
    :param kwargs: Additional keyword arguments to pass to the base operator.
    """

    def __init__(
        self,
        dag,
        **kwargs,
    ):
        """
        Constructor for the LocalAssignDataToProjectOperator.
        """
        self.dcmweb_helper = HelperDcmWeb()
        super().__init__(
            dag=dag,
            name="assign-data-to-project",
            python_callable=self.start,
            ram_mem_mb=10,
            **kwargs,
        )

    def start(self, **kwargs):
        """
        Start method for the operator.

        This method is called when the operator is executed. It collects the data from the DAG and assigns it to the specified projects.

        :param kwargs: Additional keyword arguments passed to the operator.
        """

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = os.path.join(run_dir, self.batch_name)
        print(f"{batch_folder=}")
        batch_elemtent_dirs = glob.glob(os.path.join(batch_folder, "*"))
        print(f"{batch_elemtent_dirs=}")

        for batch_element_dir in batch_elemtent_dirs:
            operator_in_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            print(f"{operator_in_dir=}")
            path_to_metadata = glob.glob(os.path.join(operator_in_dir, "*.json"))
            assert len(path_to_metadata) == 1
            path_to_metadata = path_to_metadata[0]
            self.assign_data_to_projects(path_to_metadata)

    def assign_data_to_projects(self, path_to_metadata: str) -> None:
        """ """
        with open(path_to_metadata) as f:
            metadata = json.load(f)

        series_instance_uid = metadata.get("0020000E SeriesInstanceUID_keyword")
        clinical_trial_protocol_id = metadata.get(
            "00120020 ClinicalTrialProtocolID_keyword"
        )
        project = self.get_project_by_name(clinical_trial_protocol_id)
        project_id = project.get("id")

        url = f"{self.dcmweb_helper.dcmweb_rs_endpoint}/projects/{project_id}/data/{series_instance_uid}"
        response = self.dcmweb_helper.session.put(url)
        response.raise_for_status()

    def get_project_by_name(self, project_name: str):
        response = requests.get(
            "http://aii-service.services.svc:8080/projects",
            params={"name": project_name},
        )
        response.raise_for_status()
        projects = response.json()
        try:
            return projects[0]
        except IndexError as e:
            print(f"Project {project_name} not found!")
            raise e
