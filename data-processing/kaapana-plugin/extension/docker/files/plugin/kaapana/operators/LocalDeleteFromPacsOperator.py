import glob
import os
import json
from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalDeleteFromPacsOperator(KaapanaPythonBaseOperator):
    """
    Operator to remove series from PACS system.

    This operator removes either selected series or whole studies from Kaapana's integrated PACS.
    The operator relies on the "delete_study" function of Kaapana's "HelperDcmWeb" operator.

    **Inputs:**

    * Input data which should be removed given by input parameter: input_operator.
    """

    def __init__(self, dag, delete_complete_study=False, **kwargs):
        """
        :param delete_complete_study: Specifies the amount of removed data to all series of a specified study.
        """
        self.delete_complete_study = delete_complete_study
        super().__init__(
            dag=dag, name="delete-pacs", python_callable=self.start, **kwargs
        )

    def start(self, ds, **kwargs):
        conf = kwargs["dag_run"].conf
        self.dcmweb_helper = HelperDcmWeb()
        print("conf", conf)

        self.delete_complete_study = conf.get("form_data", {}).get(
            "delete_complete_study", self.delete_complete_study
        )
        print("Delete entire study set to ", self.delete_complete_study)

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = glob.glob(os.path.join(run_dir, self.batch_name, "*"))

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
                        self.dcmweb_helper.delete_study(study_uid=study_uid)
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
                self.log.info(
                    "Deleting series: %s from study: %s", series_uid, study_uid
                )
                self.dcmweb_helper.delete_series(
                    series_uid=series_uid, study_uid=study_uid
                )
