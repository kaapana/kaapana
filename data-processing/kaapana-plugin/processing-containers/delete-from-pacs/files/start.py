import glob
import json
import logging
import os
from os import getenv

from kaapanapy.helper import load_workflow_config
from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from kaapanapy.settings import KaapanaSettings, OperatorSettings

# Set logging level
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

SERVICES_NAMESPACE = KaapanaSettings().services_namespace


class DeleteFromPacsOperator:

    def __init__(
        self,
        delete_complete_study: bool = False,
    ):
        """Initializes the operator with the given parameters.

        Args:
            delete_complete_study (bool, optional): Boolean to delete the complete study. Defaults to False.
        """
        # Set the delete_complete_study flag
        self.delete_complete_study = delete_complete_study
        # Load the workflow configuration
        self.conf = load_workflow_config()
        # Initialize the DcmWeb helper
        self.dcmweb_helper = HelperDcmWeb()

        # Airflow variables
        operator_settings = OperatorSettings()

        self.operator_in_dir = operator_settings.operator_in_dir
        self.workflow_dir = operator_settings.workflow_dir
        self.batch_name = operator_settings.batch_name
        self.run_id = operator_settings.run_id

    def start(self):

        project_form: dict = self.conf.get("project_form")

        self.delete_complete_study = self.conf.get("form_data", {}).get(
            "delete_complete_study", self.delete_complete_study
        )
        logging.info(f"Delete entire study set to {self.delete_complete_study}")

        batch_folder = [
            f for f in glob.glob(os.path.join(self.workflow_dir, self.batch_name, "*"))
        ]

        series_of_studies_which_should_be_deleted = {}

        for batch_element_dir in batch_folder:
            json_files = glob.glob(
                os.path.join(batch_element_dir, self.operator_in_dir, "*.json*"),
                recursive=True,
            )

            for meta_file in json_files:
                with open(meta_file) as fs:
                    metadata = json.load(fs)
                    series_uid = metadata["0020000E SeriesInstanceUID_keyword"]
                    study_uid = metadata["0020000D StudyInstanceUID_keyword"]

                    if self.delete_complete_study:
                        logging.info(f"Deleting study: {study_uid}")
                        self.dcmweb_helper.delete_study(
                            project_id=project_form.get("id"), study_uid=study_uid
                        )
                    else:
                        if study_uid in series_of_studies_which_should_be_deleted:
                            series_of_studies_which_should_be_deleted[study_uid].append(
                                series_uid
                            )
                        else:
                            series_of_studies_which_should_be_deleted[study_uid] = [
                                series_uid
                            ]

        # If we are not deleting the complete study, we need to delete the series one by one
        for study_uid, series_uids in series_of_studies_which_should_be_deleted.items():
            for series_uid in series_uids:
                logging.info(f"Deleting series: {series_uid} from study: {study_uid}")
                self.dcmweb_helper.delete_series(
                    project_id=project_form.get("id"),
                    study_uid=study_uid,
                    series_uid=series_uid,
                )


if __name__ == "__main__":

    delete_complete_study = getenv("DELETE_COMPLETE_STUDY", "false").lower() == "true"

    operator = DeleteFromPacsOperator(
        delete_complete_study=delete_complete_study,
    )

    operator.start()
