import glob
import json
import os
import re

import requests
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.helper import get_opensearch_client, get_minio_client
from kaapanapy.helper.HelperOpensearch import DicomTags
from kaapanapy.settings import OpensearchSettings


class LocalClearValidationResultOperator(KaapanaPythonBaseOperator):
    """
    This Operator delete validation results from minio.

    Attributes:
        minio_client (Minio): MinIO client for interacting with the MinIO service.
        os_client (OpenSearch): OpenSearch client for interacting with the OpenSearch service.
        validation_field (str): Field in the OpenSearch index used for validation results.
        result_bucket (str): minio bucket which stores the validation results html files.
        opensearch_index (str): Index in OpenSearch where metadata is stored.
        apply_project_context (bool): (Additional) If set to true, will look for ClinicalTrialProtocolID in the DICOM metadata and
                set the bucket and opensearch index from the metadata JSON file.
    """

    def get_project_by_name(self, project_name: str):
        response = requests.get(
            f"http://aii-service.{SERVICES_NAMESPACE}.svc:8080/projects/{project_name}",
            params={"name": project_name},
        )
        response.raise_for_status()
        project = response.json()
        return project

    def get_project_config_from_meta_json(self, json_dict):
        ctp_value = json_dict.get("00120020 ClinicalTrialProtocolID_keyword")

        if ctp_value:
            if isinstance(ctp_value, list):
                clinical_trial_protocol_id = ctp_value[0]
            else:
                clinical_trial_protocol_id = str(ctp_value)

            project = self.get_project_by_name(clinical_trial_protocol_id)
            if project:
                return project
        else:
            print("ClinicalTrialProtocolID not found in the provided Metadata JSON")

        return None

    def get_all_files_from_result_bucket(self, prefix=""):
        """
        Recursively retrieves all files from the specified MinIO bucket `staticwebsiteresults`.

        Args:
            prefix (str): The prefix to filter the objects in the MinIO bucket. Defaults to an empty string.

        Returns:
            list: A list of file paths in the specified MinIO bucket.
        """
        allresults = self.minio_client.list_objects(self.result_bucket, prefix)
        files = []
        for item in allresults:
            if item.is_dir:
                files.extend(
                    self.get_all_files_from_result_bucket(prefix=item.object_name)
                )
            else:
                files.append(item.object_name)
        return files

    def remove_field_in_opensearch(self, seriesuid: str, tagfield: str = ""):
        """
        Removes a specified field from a document in OpenSearch.

        Args:
            seriesuid (str): The unique identifier for the series in OpenSearch.
            tagfield (str): The field to be removed from the document. Defaults to the class attribute `validation_field`.

        Returns:
            None
        """
        if tagfield == "":
            tagfield = self.validation_field

        # Update the document to remove the field
        response = self.os_client.update(
            index=self.opensearch_index,
            id=seriesuid,
            body={
                "script": {
                    "source": "ctx._source.remove(params.field)",
                    "lang": "painless",
                    "params": {"field": tagfield},
                }
            },
        )

        if response["result"] == "updated":
            print(f"{tagfield} is deleted from the {seriesuid} in OpenSearch")
        else:
            print(
                f"Warning!! {tagfield} could not be deleted from the {seriesuid} document in OpenSearch"
            )

        return

    def remove_from_minio(self, seriesuid: str):
        """
        Deletes all validation results for a given series from MinIO bucket `staticwebsiteresults`.

        Args:
            seriesuid (str): The unique identifier for the series to be deleted from MinIO.

        Returns:
            None
        """
        allfiles = self.get_all_files_from_result_bucket()

        # match only the files placed under the subdirectory of serisuid
        sereismatcher = re.compile(fr"\/?{re.escape(seriesuid)}\/")
        seriesresults = [s for s in allfiles if sereismatcher.search(s)]

        if len(seriesresults) == 0:
            print(f"No validation results found in minio for series {seriesuid}")
            return

        for result in seriesresults:
            self.minio_client.remove_object(
                bucket_name=self.result_bucket, object_name=result
            )
            print(f"{result} is removed from minio")

        return

    def _init_clients(self, dag_run):
        """
        Initializes the MinIO Client and the Opensearch client.

        Args:
            dag_run (DAGRun): The current DAG run instance providing context and configuration.

        Returns:
            None
        """
        # initialize MinIO client
        self.minio_client = get_minio_client()
        # Point to the already initialized HelperOpensearch client
        self.os_client = get_opensearch_client()

    def start(self, ds, **kwargs):
        """
        Main execution method called by Airflow to run the operator.

        Args:
            ds (str): The execution date as a string.
            **kwargs: Additional keyword arguments provided by Airflow.

        Returns:
            None
        """
        dag_run = kwargs["dag_run"]
        conf = kwargs["dag_run"].conf
        print("Start Deleting Validation results")

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = [
            f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))
        ]

        self._init_clients(dag_run)

        for batch_element_dir in batch_folder:
            jsonfiles = sorted(
                glob.glob(
                    os.path.join(batch_element_dir, self.operator_in_dir, "*.json*"),
                    recursive=True,
                )
            )

            for metafile in jsonfiles:
                print(f"Deleting validation results for file {metafile}")

                with open(metafile) as fs:
                    metadata = json.load(fs)

                # if `apply_project_context` is set to true,
                # it will look for the project config using the ClinicalTrialProtocolID
                # from the DICOM metadata JSON and use the project bucket and project OS index
                # to clear the results
                if self.apply_project_context:
                    project_config = self.get_project_config_from_meta_json(metadata)
                    if project_config:
                        self.result_bucket = project_config["s3_bucket"]
                        self.opensearch_index = project_config["opensearch_index"]

                seriesuid = metadata[
                    DicomTags.series_uid_tag
                ]  # "0020000E SeriesInstanceUID_keyword"

                self.remove_from_minio(seriesuid)
                self.remove_field_in_opensearch(
                    seriesuid, tagfield=self.validation_field
                )

    def __init__(
        self,
        dag,
        name: str = "clear-validation-results",
        result_bucket: str = "staticwebsiteresults",
        validation_tag: str = "00111001",
        opensearch_index=None,
        apply_project_context=None,
        *args,
        **kwargs,
    ):
        """
        Initializes the LocalClearValidationResultOperator.

        Args:
            dag (DAG): The DAG to which the operator belongs.
            name (str): The name of the operator. Defaults to "clear-validation-results".
            results_bucket (str): minio bucket which stores the validation results html files. Defaults to "staticwebsiteresults".
            validation_tag (str): Base tag used to store validation results on OpenSearch (default: "00111001").
            opensearch_index (str): Index in OpenSearch where metadata will be stored. Defaults to OpensearchSettings().default_index.
            apply_project_context (bool): (Additional) If set to true, will look for ClinicalTrialProtocolID in the DICOM metadata and
                set the bucket and opensearch index from the metadata JSON file.
            *args: Additional arguments for the parent class.
            **kwargs: Additional keyword arguments for the parent class.

        Returns:
            None
        """
        self.minio_client = None
        self.os_client = None
        self.validation_field = f"{validation_tag} ValidationResults_object"
        self.result_bucket = result_bucket
        self.opensearch_index = opensearch_index or OpensearchSettings().default_index
        self.apply_project_context = bool(apply_project_context)

        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
