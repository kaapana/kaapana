import os
import glob
import pydicom

import requests

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE


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
        projects: list = [],
        **kwargs,
    ):
        """
        Constructor for the LocalAssignDataToProjectOperator.
        """
        self.projects = projects
        self.projects_api = f"http://aii-service.{SERVICES_NAMESPACE}.svc:8080"

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
        self.run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        data_to_send = self.collect_data_from_dag()
        for data in data_to_send:
            for project in self.projects:
                self.assign_data_to_project(project, data)

    def collect_data_from_dag(self):
        """
        Collect data from the DAG.

        This method collects DICOM series data from the specified directory in the DAG run directory.

        :return: A list of data dictionaries to send to the projects.
        """
        data_to_send = []
        batch_folders = [
            f for f in glob.glob(os.path.join(self.run_dir, self.batch_name, "*"))
        ]

        for batch_element_dir in batch_folders:
            element_input_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            print(element_input_dir)

            dcm_files = sorted(
                glob.glob(os.path.join(element_input_dir, "**/*.dcm*"), recursive=True)
            )
            for series_file in dcm_files:
                dicom_data = pydicom.dcmread(series_file)
                series_uid = str(dicom_data[0x0020, 0x000E].value)

                data = {
                    "description": "DICOM series",
                    "data_type": "dicom-series", #TODO: Commit on standard data types
                    "data_storage_id": series_uid,
                }
                data_to_send.append(data)
        return data_to_send

    def assign_data_to_project(self, project: str, data: dict):
        """
        Assign data to a project.

        This method sends the data dictionary to the specified project using the Access Information Interface (AII) API.

        :param project: The name of the project to assign the data to.
        :param data: The data dictionary to send to the project.
        """
        response = requests.post(
            f"{self.projects_api}/projects/{project}/data", json=data
        )
        response.raise_for_status()
