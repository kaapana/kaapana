import glob
import os
import json
import logging
from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalDeleteFromPacsOperator(KaapanaPythonBaseOperator):
    """
    Operator to remove series from PACS system.

    This operator removes either selected series or whole studies from Kaapana's integrated research PACS system by DCM4Chee.
    The operaator relies on "delete_study" function of Kaapana's "HelperDcmWeb" operator.

    **Inputs:**

    * Input data which should be removed given by input parameter: input_operator.
    """

    def start(self, ds, **kwargs):
        conf = kwargs['dag_run'].conf
        print('conf', conf)
        if 'form_data' in conf \
                and conf['form_data'] is not None \
                and 'delete_complete_study' in conf['form_data']:
            self.delete_complete_study = conf['form_data']['delete_complete_study']
            print('Delete entire study set to ', self.delete_complete_study)
        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]
        
        study2series_deletion = {}
        
        for batch_element_dir in batch_folder:
            json_files = sorted(glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.json*"), recursive=True))
            for meta_files in json_files:
                with open(meta_files) as fs:
                    metadata = json.load(fs)
                    series_uid = metadata['0020000E SeriesInstanceUID_keyword']
                    study_uid = metadata['0020000D StudyInstanceUID_keyword']

                    if self.delete_complete_study:
                        HelperDcmWeb.delete_study(
                            aet = self.pacs_aet,
                            study_uid = metadata['0020000D StudyInstanceUID_keyword']
                        )
                    else:
                        # If multiple series of one study should be delete this would combine the request
                        if study_uid in study2series_deletion:
                            study2series_deletion[study_uid].append(series_uid)
                        else:
                            study2series_deletion[study_uid] = [series_uid]

        for study_uid, series_uids in study2series_deletion.items():
            self.log.info("Deleting series: %s from study: %s", series_uids, study_uid)
            HelperDcmWeb.delete_series(
                aet = self.pacs_aet,
                series_uids = series_uids,
                study_uid = study_uid,
            )


    def __init__(self,
                 dag,
                 pacs_host='dcm4chee-service.store.svc',
                 pacs_port=8080,
                 pacs_aet='KAAPANA',
                 delete_complete_study=False,
                 wait_time=5,
                 **kwargs):
        """
        :param pacs_host: Needed to specify "pacs_dcmweb_endpoint".
        :param pacs_port: Needed to specify "pacs_dcmweb_endpoint".
        :param pacs_aet: Is by default set to "KAAPANA" and is used as a template AE-title for "HelperDcmWeb"'s "delete_study" function.
        :param delete_complete_study: Specifies the amount of removed data to all series of a specified study.
        """

        self.pacs_host = pacs_host
        self.pacs_port = pacs_port
        self.pacs_dcmweb_endpoint = "http://{}:{}".format(pacs_host, pacs_port)
        self.pacs_aet = pacs_aet
        self.wait_time = wait_time
        self.delete_complete_study = delete_complete_study

        super().__init__(
            dag=dag,
            name='delete-pacs',
            python_callable=self.start,
            **kwargs
        )