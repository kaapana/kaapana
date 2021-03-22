import glob
import os
import requests
import time
import json
from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalDeleteFromPacsOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):
        conf = kwargs['dag_run'].conf
        print('conf', conf)
        if 'conf' in conf \
                and 'form_data' in conf['conf'] \
                and conf['conf']['form_data'] is not None \
                and 'delete_complete_study' in conf['conf']['form_data']:
                self.delete_complete_study = conf['conf']['form_data']['delete_complete_study']
                print('Delete entire study set to ', self.delete_complete_study)
        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]
        dicoms_to_delete = []
        for batch_element_dir in batch_folder:
            json_files = sorted(glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.json*"), recursive=True))
            for meta_files in json_files:
                with open(meta_files) as fs:
                    metadata = json.load(fs)
                    dicoms_to_delete.append({
                        'study_uid': metadata['0020000D StudyInstanceUID_keyword'],
                        'series_uid':  metadata['0020000E SeriesInstanceUID_keyword']
                    })

        for dcm_to_delete in dicoms_to_delete:
            study_uid = dcm_to_delete['study_uid']
            series_uid = dcm_to_delete['series_uid']
            print("####################")
            print("#")
            print("# Deleting:")
            print("#")
            print(f"Study: {study_uid}")
            if series_uid:
                print(f"Series: {series_uid}")
            else:
                print("Removing entire study")
            print("#")
            print("# -> rejecting ...")
            self.reject_files(study_uid, series_uid)
            time.sleep(self.wait_time)
            print("# -> check removed from aet " + self.pacs_aet)
            self.check_removed(study_uid=study_uid, series_uid=series_uid,
                                 aet=self.pacs_aet)
            print('# -> deleting ...')
            self.delete_icom_quality_study_from_pacs(study_uid)
            time.sleep(self.wait_time)
            print('# -> check if removed ...')
            self.check_removed(study_uid=study_uid, series_uid=series_uid,
                                 aet="IOCM_QUALITY")
            if series_uid:
                print('Series {} was sucessfully deleted from PACs'.format(series_uid))
            else:
                print('Study {} was sucessfully deleted from PACs'.format(study_uid))
            print('#')

    def reject_files(self, study_uid, series_uid):
        if self.delete_complete_study:
            print(f"Check if the series UID {study_uid} can be found in AET {self.pacs_aet}")
            r = HelperDcmWeb.qidoRs(self.pacs_aet, study_uid)
        else:
            print(f"Check if the series UID {series_uid} can be found in AET {self.pacs_aet}")
            r = HelperDcmWeb.qidoRs(self.pacs_aet, study_uid, series_uid)
        if r.status_code == requests.codes.ok:
            self.reject_dicoms_icom_quality(study_uid=study_uid, series_uid=series_uid)
        elif r.status_code == 204:
            print("The search completed successfully, but there were zero results.")
        else:
            print('Error while searching and rejecting for study: {}'.format(study_uid))
            print(r.reason)
            print(r.content)
            exit(1)

    def reject_dicoms_icom_quality(self, study_uid, series_uid):
        print("reject_dicoms_icom_quality:")
        print("StudyUID: {}".format(study_uid))
        if self.delete_complete_study:
            print("Delete entire study, set seriesUID to None!")
            series_uid = None
        else:
            print("SeriesUID: {}".format(series_uid))
        r = HelperDcmWeb.rejectDicoms(studyUID=study_uid, seriesUID=series_uid)
        if r.status_code != requests.codes.ok and r.status_code != 204:
            if self.delete_complete_study:
                print('error while rejecting study_uid: {}'.format(study_uid))
            else:
                print('error while rejecting series: {}'.format(series_uid))
            print(r.reason)
            print(r.content)
            exit(1)
        else:
            print("Rejected: {}".format(study_uid))

    def delete_icom_quality_study_from_pacs(self, rejected_study_uid):
        print("Check if the series UID", rejected_study_uid, "can be found in AET ", "IOCM_QUALITY")
        r = HelperDcmWeb.qidoRs(aet="IOCM_QUALITY", studyUID=rejected_study_uid)
        if r.status_code == requests.codes.ok:
            print("Delete_icom_quality_study_from_pacs StudyID: {}".format(rejected_study_uid))
            r = HelperDcmWeb.deleteStudy(rejected_study_uid)
            if r.status_code != requests.codes.ok and r.status_code != 204:
                print('error delete_icom_quality_study_from_pacs ?!')
                print(r.reason)
                print(r.content)
                exit(1)
            else:
                print("Deleted: {}".format(rejected_study_uid))
        elif r.status_code == 204:
            print("The search completed successfully, but there were zero results in IOCM_QUALITY.")
        else:
            print('Error while searching and rejecting for study: {} in IOCM_QUALITY'.format(rejected_study_uid))
            print(r.reason)
            print(r.content)
            exit(1)

    def check_removed(self, study_uid, series_uid, aet):
        if self.delete_complete_study:
            print("Check if there are no more traces of the study UID", study_uid)
            r = HelperDcmWeb.qidoRs(aet, study_uid)
        else:
            print("Check if there are no more traces of the series UID", series_uid)
            r = HelperDcmWeb.qidoRs(aet, study_uid, series_uid)
        if r.status_code != 204:
            print('error series still found in PACs, AET ', aet)
            print(r.reason)
            print(r.content)
            exit(1)
        print('Series {} was sucessfully deleted from PACs'.format(series_uid))

    def __init__(self,
                 dag,
                 pacs_host='dcm4chee-service.store.svc',
                 pacs_port=8080,
                 pacs_aet='KAAPANA',
                 wait_time=5,
                 *args, **kwargs):

        self.pacs_host = pacs_host
        self.pacs_port = pacs_port
        self.pacs_dcmweb_endpoint = "http://{}:{}".format(pacs_host, pacs_port)
        self.pacs_aet = pacs_aet
        self.wait_time = wait_time


        super().__init__(
            dag,
            name='delete-pacs',
            python_callable=self.start,
            *args, **kwargs
        )
