import glob
import json
import os
from os import getenv
from os.path import exists

import pydicom
from kaapanapy.helper.HelperOpensearch import HelperOpensearch
from kaapanapy.logger import get_logger
from kaapanapy.settings import KaapanaSettings, OperatorSettings

logger = get_logger(__name__, level="INFO")

SERVICES_NAMESPACE = KaapanaSettings().services_namespace


class DeleteFromMetaOperator:
    """This operator removes either selected series or whole studies from OpenSearch's project index."""

    def __init__(
        self,
        delete_complete_study: bool = False,
        delete_all_documents: bool = False,
    ):
        """Initializes the operator with the given parameters.

        Args:
            delete_complete_study (bool, optional): Boolean to delete the complete study. Defaults to False.
            delete_all_documents (bool, optional): Boolean to delete all documents. Defaults to False.
        """
        self.delete_complete_study = delete_complete_study
        self.delete_all_documents = delete_all_documents

        # Airflow variables
        operator_settings = OperatorSettings()

        self.operator_in_dir = operator_settings.operator_in_dir
        self.workflow_dir = operator_settings.workflow_dir
        self.batch_name = operator_settings.batch_name
        self.run_id = operator_settings.run_id

        config_path = os.path.join(self.workflow_dir, "conf", "conf.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                self.workflow_config = json.load(f)

        if not self.delete_complete_study:
            if (
                "form_data" in self.workflow_config
                and self.workflow_config["form_data"] is not None
                and "delete_complete_study" in self.workflow_config["form_data"]
            ):
                self.delete_complete_study = self.workflow_config["form_data"][
                    "delete_complete_study"
                ]
        logger.info(f"Delete entire study set to {self.delete_complete_study}")

        if not self.delete_all_documents:
            if (
                "form_data" in self.workflow_config
                and self.workflow_config["form_data"] is not None
                and "delete_all_documents" in self.workflow_config["form_data"]
            ):
                self.delete_all_documents = self.workflow_config["form_data"][
                    "delete_all_documents"
                ]
        logger.info(f"Delete all documents set to {self.delete_all_documents}")

    def start(self):
        """Starts the operator."""

        if self.delete_all_documents:
            logger.info("Deleting all documents from META ...")
            query = {"query": {"match_all": {}}}

            # Delete from project index
            HelperOpensearch.delete_by_query(query)

        else:
            batch_folder = [
                f
                for f in glob.glob(
                    os.path.join(self.workflow_dir, self.batch_name, "*")
                )
            ]

            dicoms_to_delete = []
            for batch_element_dir in batch_folder:
                dcm_files = sorted(
                    glob.glob(
                        os.path.join(batch_element_dir, self.operator_in_dir, "*.dcm*"),
                        recursive=True,
                    )
                )
                if len(dcm_files) > 0:
                    incoming_dcm = pydicom.dcmread(dcm_files[0])
                    series_uid = incoming_dcm.SeriesInstanceUID
                    study_uid = incoming_dcm.StudyInstanceUID
                    if self.delete_complete_study:
                        dicoms_to_delete.append(study_uid)
                    else:
                        dicoms_to_delete.append(series_uid)
                else:
                    json_files = sorted(
                        glob.glob(
                            os.path.join(
                                batch_element_dir, self.operator_in_dir, "*.json*"
                            ),
                            recursive=True,
                        )
                    )
                    for meta_files in json_files:
                        with open(meta_files) as fs:
                            metadata = json.load(fs)
                            dicoms_to_delete.append(
                                {
                                    "study_uid": metadata[
                                        "0020000D StudyInstanceUID_keyword"
                                    ],
                                    "series_uid": metadata[
                                        "0020000E SeriesInstanceUID_keyword"
                                    ],
                                }
                            )

            if self.delete_complete_study:
                query = {
                    "query": {
                        "terms": {"0020000D StudyInstanceUID_keyword": dicoms_to_delete}
                    }
                }
            else:
                query = {"query": {"terms": {"_id": dicoms_to_delete}}}

            HelperOpensearch.delete_by_query(query)


if __name__ == "__main__":

    delete_complete_study = getenv("DELETE_COMPLETE_STUDY", False)
    delete_complete_study = delete_complete_study.lower() == "true"

    delete_all_documents = getenv("DELETE_ALL_DOCUMENTS", False)
    delete_all_documents = delete_all_documents.lower() == "true"

    operator = DeleteFromMetaOperator(
        delete_complete_study=delete_complete_study,
        delete_all_documents=delete_all_documents,
    )

    operator.start()
