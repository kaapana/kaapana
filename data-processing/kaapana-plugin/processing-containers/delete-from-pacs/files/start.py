import glob
import json
import logging
import os
from os import getenv

# pydicom is needed to read Study/Series UIDs directly from raw DICOM input files,
# so this container can also run after operators that provide DICOMs instead of
# metadata JSON (e.g. LocalGetInputDataOperator in service workflows).
import pydicom

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
        """Starts the operator to delete the series from the PACS system."""

        project_form: dict = self.conf.get("project_form")

        self.delete_complete_study = self.conf.get("workflow_form", {}).get(
            "delete_complete_study", self.delete_complete_study
        )
        logging.info(f"Delete entire study set to {self.delete_complete_study}")

        batch_folder = [
            f for f in glob.glob(os.path.join(self.workflow_dir, self.batch_name, "*"))
        ]
        # Log the resolved input location up front: when a delete run removes nothing,
        # the first thing to check is whether the operator looked in the right place.
        logging.info(
            "Scanning PACS delete input: workflow_dir=%s, batch_name=%s, operator_in_dir=%s, batch_elements=%d",
            self.workflow_dir,
            self.batch_name,
            self.operator_in_dir,
            len(batch_folder),
        )

        # Service workflows can hand this processing container either metadata-json
        # or raw DICOM input. Normalize both inputs to study/series UIDs so the
        # PACS delete logic works for monitoring runs without DAG-specific images.
        series_of_studies_which_should_be_deleted = {}
        studies_which_should_be_deleted = set()
        # Diagnostic counters only: they show in the summary log which input style
        # (DICOM vs. metadata JSON) each batch element was resolved from.
        dcm_batch_count = 0
        json_batch_count = 0

        for batch_element_dir in batch_folder:
            # Check for raw DICOM input first ("*.dcm*" also matches ".dcm.gz" etc.).
            # sorted() makes the "read the first file" pick below deterministic.
            dcm_files = sorted(
                glob.glob(
                    os.path.join(batch_element_dir, self.operator_in_dir, "*.dcm*"),
                    recursive=True,
                )
            )

            if dcm_files:
                dcm_batch_count += 1
                # Monitoring extractor runs hand the delete container downloaded DICOMs
                # from LocalGetInputDataOperator, so derive the deletion target directly
                # from the first file in the batch element instead of requiring metadata.
                incoming_dcm = pydicom.dcmread(dcm_files[0], stop_before_pixels=True)
                series_uid = incoming_dcm.SeriesInstanceUID
                study_uid = incoming_dcm.StudyInstanceUID

                if self.delete_complete_study:
                    # Whole-study deletes must be deduplicated because one study can
                    # appear in multiple batch elements or multiple series inputs.
                    studies_which_should_be_deleted.add(study_uid)
                else:
                    # Preserve the original per-series delete behavior for workflows
                    # that intentionally delete only a subset of a study.
                    series_of_studies_which_should_be_deleted.setdefault(
                        study_uid, []
                    ).append(series_uid)
                continue

            # Keep backward compatibility for workflows that already provide the
            # metadata-json structure expected by earlier delete-from-pacs images.
            json_files = glob.glob(
                os.path.join(batch_element_dir, self.operator_in_dir, "*.json*"),
                recursive=True,
            )
            if json_files:
                json_batch_count += 1

            for meta_file in json_files:
                with open(meta_file) as fs:
                    metadata = json.load(fs)
                    series_uid = metadata["0020000E SeriesInstanceUID_keyword"]
                    study_uid = metadata["0020000D StudyInstanceUID_keyword"]

                    if self.delete_complete_study:
                        # JSON-based study deletes share the same deduplication path as
                        # DICOM-based deletes so both input styles behave identically.
                        studies_which_should_be_deleted.add(study_uid)
                    else:
                        series_of_studies_which_should_be_deleted.setdefault(
                            study_uid, []
                        ).append(series_uid)

        # Summarize what was resolved before any delete request is sent, so the task
        # log documents the intended scope even if a later DICOMweb call fails.
        logging.info(
            "Resolved PACS delete candidates from input: dcm_batches=%d, json_batches=%d, study_deletes=%d, series_deletes=%d",
            dcm_batch_count,
            json_batch_count,
            len(studies_which_should_be_deleted),
            sum(len(series_uids) for series_uids in series_of_studies_which_should_be_deleted.values()),
        )

        if self.delete_complete_study:
            if not studies_which_should_be_deleted:
                # Emit an explicit warning so "successful but deleted nothing" runs are
                # visible in task logs during service-workflow troubleshooting.
                logging.warning(
                    "Resolved 0 PACS delete candidates from %s; nothing will be deleted.",
                    self.operator_in_dir,
                )
            deleted_study_count = 0
            for study_uid in sorted(studies_which_should_be_deleted):
                # Keep the concrete study UID in the log so operators can verify the
                # series disappeared from gallery views and DICOMweb queries.
                logging.info(f"Deleting study: {study_uid}")
                self.dcmweb_helper.delete_study(
                    project_id=project_form.get("id"), study_uid=study_uid
                )
                deleted_study_count += 1
            # Counts delete requests, not objects: one study delete implicitly removes
            # all series of that study, so no per-series requests are issued here.
            logging.info(
                "Finished PACS delete run: deleted_studies=%d (each including all its series), no separate series deletes issued",
                deleted_study_count,
            )

        # If we are not deleting the complete study, we need to delete the series one by one
        if (
            not self.delete_complete_study
            and not series_of_studies_which_should_be_deleted
        ):
            # Match the whole-study warning for series-scoped deletes so empty inputs
            # are never mistaken for a successful removal.
            logging.warning(
                "Resolved 0 PACS delete candidates from %s; nothing will be deleted.",
                self.operator_in_dir,
            )
        deleted_series_count = 0
        for study_uid, series_uids in series_of_studies_which_should_be_deleted.items():
            for series_uid in series_uids:
                # Per-series logs remain important when callers intentionally retain
                # other series from the same study.
                logging.info(f"Deleting series: {series_uid} from study: {study_uid}")
                self.dcmweb_helper.delete_series(
                    project_id=project_form.get("id"),
                    study_uid=study_uid,
                    series_uid=series_uid,
                )
                deleted_series_count += 1
        if not self.delete_complete_study:
            logging.info(
                "Finished PACS delete run: deleted_series=%d, no whole-study deletes issued",
                deleted_series_count,
            )


if __name__ == "__main__":

    delete_complete_study = getenv("DELETE_COMPLETE_STUDY", "false").lower() == "true"

    operator = DeleteFromPacsOperator(
        delete_complete_study=delete_complete_study,
    )

    operator.start()
