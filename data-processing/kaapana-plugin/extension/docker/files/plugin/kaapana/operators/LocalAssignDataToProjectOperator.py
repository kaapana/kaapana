import os

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from kaapanapy.logger import get_logger
from kaapanapy.settings import KaapanaSettings
import glob
import json
import requests

logger = get_logger(__name__)

SERVICES_NAMESPACE = KaapanaSettings().services_namespace


class LocalAssignDataToProjectOperator(KaapanaPythonBaseOperator):
    """
    Operator to assign data to projects in Kaapana.

    This operator collects all metadata files in the operator_in_dir of all series processed in the DAG-run.
    It calls the dicom-web-filter API to create a DataProject mapping for each series based on the tag 00120020 ClinicalTrialProtocolID_keyword stored in the metadata file.

    :param dag: The DAG object associated with the operator.
    :param kwargs: Additional keyword arguments to pass to the base operator.
    """

    def __init__(
        self,
        dag,
        from_other_project=False,
        **kwargs,
    ):
        """
        Constructor for the LocalAssignDataToProjectOperator.
        """
        self.dcmweb_helper = HelperDcmWeb()
        self.from_other_project = from_other_project
        super().__init__(
            dag=dag,
            name="assign-data-to-project",
            python_callable=self.create_project_mappings_for_all_series,
            ram_mem_mb=10,
            **kwargs,
        )

    def create_project_mappings_for_all_series(self, **kwargs):
        """
        Create DataProjects mappings in the Dicom-Web-Filter for all metadata files of all series in the batch directory of the workflow.
        It is expected, that the operator_in_dir contains a single .json file containing the metadata of the dicom series.

        :param kwargs: Additional keyword arguments passed to the operator.
        """

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = os.path.join(run_dir, self.batch_name)
        batch_elemtent_dirs = glob.glob(os.path.join(batch_folder, "*"))

        for batch_element_dir in batch_elemtent_dirs:
            operator_in_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            logger.info(f"{operator_in_dir=}")
            path_to_metadata = glob.glob(os.path.join(operator_in_dir, "*.json"))
            assert len(path_to_metadata) == 1
            path_to_metadata = path_to_metadata[0]
            with open(path_to_metadata) as f:
                metadata = json.load(f)
            if self.from_other_project:
                config = kwargs["dag_run"].conf
                from_data = config.get("form_data")
                projects = from_data.get("projects")
                series_instance_uid = metadata.get("0020000E SeriesInstanceUID_keyword")
                for project in projects:
                    self.add_data_to_project(series_instance_uid, project_name=project)
            else:    
                self.assign_data_to_projects(metadata)

    def assign_data_to_projects(self, metadata) -> None:
        """
        Map a dicom series to a project in the Dicom-Web-Filter based on the dicom metadata stored in path_to_metadata.
        The project name is stored in the metadata as the key '00120020 ClinicalTrialProtocolID_keyword'
        Additionally map the series to the admin project.
        """
        series_instance_uid = metadata.get("0020000E SeriesInstanceUID_keyword")
        study_uid = metadata.get("0020000D StudyInstanceUID_keyword")
        clinical_trial_protocol_id = metadata.get(
            "00120020 ClinicalTrialProtocolID_keyword"
        )

        ### Create the series as datapoint in the dicom-web-filter
        payload = {"study_uid": study_uid, "description": "Dicom data"}
        logger.debug(payload)
        url = f"{self.dcmweb_helper.dcmweb_rs_endpoint}/data/{series_instance_uid}"
        response = self.dcmweb_helper.session.put(url, params=payload)
        response.raise_for_status()

        ### Create the project-data mapping for the admin project
        self.add_data_to_project(series_instance_uid, project_id=1)
        logger.debug(f"Added {series_instance_uid} to admin project with id 1.")

        if type(clinical_trial_protocol_id) == list:
            assert len(clinical_trial_protocol_id) == 1
            clinical_trial_protocol_id = clinical_trial_protocol_id[0]

        ### Create the project-data mapping for the project stored in the dicom tag: ClinicalTrialProtocolID_keyword
        try:
            self.add_data_to_project(series_instance_uid, project_name=clinical_trial_protocol_id)
        except (IndexError, requests.exceptions.HTTPError) as e:
            logger.warning(
                f"{series_instance_uid=} is not assigned to a project! This does not fail the task. The series will still be assigned to the default admin project, when the data arrives at the Dicom-Web-Filter: {e}"
            )
            return None

    def add_data_to_project(self, series_instance_uid, project_id=None, project_name=None):
        """
        Assigns a DICOM series to a project using either the project ID or project name.

        Args:
            series_instance_uid (str): The unique identifier of the DICOM series.
            project_id (str, optional): The ID of the project to assign the series to.
            project_name (str, optional): The name of the project to assign the series to.

        Raises:
            ValueError: If neither `project_id` nor `project_name` is provided.
            ValueError: If `project_name` is provided but does not resolve to a valid project.
            requests.HTTPError: If the request to assign the data fails.
        """
        if not project_id and not project_name:
            raise ValueError("Either 'project_id' or 'project_name' must be provided.")

        if project_name:
            project = self.get_project_by_name(project_name)
            if not project:
                raise ValueError(f"Project with name '{project_name}' not found.")
            project_id = project.get("id")

        url = f"{self.dcmweb_helper.dcmweb_rs_endpoint}/projects/{project_id}/data/{series_instance_uid}"
        response = self.dcmweb_helper.session.put(url)
        response.raise_for_status()
        
        logger.debug(f"Added {series_instance_uid} to project with {project_id=}")

    def get_project_by_name(self, project_name: str):
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
