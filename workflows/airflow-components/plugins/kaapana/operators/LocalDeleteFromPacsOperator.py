import glob
import os
from datetime import timedelta
from urllib.error import URLError, HTTPError
import urllib.request
from elasticsearch import Elasticsearch
from elasticsearch import helpers
import pydicom
import requests
import time
import json

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalDeleteFromPacsOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):

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

        print('dicoms to delete')
        for dcm in dicoms_to_delete:
            print('####################')
            print(dcm['study_uid'])
            print(dcm['series_uid'])

        for dcm_to_delete in dicoms_to_delete:
            if self.delete_complete_study:
                self.reject_study_icom_quality(dcm_to_delete['study_uid'])
            else:
                self.reject_series_icom_quality(study_uid=dcm_to_delete['study_uid'], series_uid=dcm_to_delete['series_uid'])

            self.delete_icom_quality_study_from_pacs(dcm_to_delete['study_uid'])
            self.check_all_clean(study_uid=dcm_to_delete['study_uid'], series_uid=dcm_to_delete['series_uid'])

    def reject_study_icom_quality(self, study_uid):
        print("Reject_study_icom_quality:")
        print("StudyUID: {}".format(study_uid))

        reject_url = "{}/dcm4chee-arc/aets/KAAPANA/rs/studies/{}/reject/113001%5EDCM".format(self.pacs_dcmweb_endpoint, study_uid)
        r = requests.post(reject_url, verify=False)
        if r.status_code != requests.codes.ok and r.status_code != 204:
            print('error while rejecting study: {}'.format(study_uid))
            print(r.reason)
            print(r.content)
            if r.status_code == 404:
                print("Study not found, continue checking if in rejected.")
            else:
                exit(1)
        else:
            print("Rejected: {}".format(study_uid))

    def reject_series_icom_quality(self, study_uid, series_uid):
        print("Reject_series_icom_quality:")
        print("StudyUID: {}".format(study_uid))
        print("SeriesUID: {}".format(series_uid))
        reject_url = "{}/dcm4chee-arc/aets/KAAPANA/rs/studies/{}/series/{}/reject/113001%5EDCM".format(self.pacs_dcmweb_endpoint, study_uid, series_uid)
        r = requests.post(reject_url, verify=False)
        # {"count":1}
        if r.status_code != requests.codes.ok and r.status_code != 204:
            print('error while rejecting series: {}'.format(series_uid))
            print(r.reason)
            print(r.content)
            if r.status_code == 404:
                print("Series not found, continue checking if already deleted.")
            else:
                exit(1)
        else:
            print("Rejected: {}".format(study_uid))

    def delete_icom_quality_study_from_pacs(self, rejected_study_uid):
        print("Delete_icom_quality_study_from_pacs StudyID: {}".format(rejected_study_uid))
        reject_url = "{}/dcm4chee-arc/aets/IOCM_QUALITY/rs/studies/{}".format(self.pacs_dcmweb_endpoint,
                                                                              rejected_study_uid)
        r = requests.delete(reject_url, verify=False)
        if r.status_code != requests.codes.ok and r.status_code != 204:
            print('error delete_icom_quality_study_from_pacs ?!')
            print(r.reason)
            print(r.content)
            exit(1)
        else:
            print("Deleted: {}".format(rejected_study_uid))


    def check_all_clean(self, study_uid, series_uid):
        print("Check if there are no more traces of the UID", series_uid)
        r = requests.get("{}/dcm4chee-arc/aets/KAAPANA/rs/studies/{}/series/{}/instances"
                         .format(self.pacs_dcmweb_endpoint, study_uid, series_uid), verify=False)
        if r.status_code != 204:
            print('error series still found in PACs, AET KAAPANA')
            print(r.reason)
            print(r.content)
            exit(1)

        r = requests.get("{}/dcm4chee-arc/aets/IOCM_QUALITY/rs/studies/{}/series/{}/instances"
                         .format(self.pacs_dcmweb_endpoint, study_uid, series_uid), verify=False)
        if r.status_code != 204:
            print('error series still found in PACs, AET IOCM_QUALITY')
            print(r.reason)
            print(r.content)
            exit(1)
        print('Series {} was sucessfully deleted from PACs'.format(series_uid))

    def __init__(self,
                 dag,
                 delete_operator=None,
                 pacs_host='dcm4chee-service.store.svc',
                 pacs_port=8080,
                 delete_complete_study=False,
                 *args, **kwargs):

        self.pacs_host = pacs_host
        self.pacs_port = pacs_port
        self.pacs_dcmweb_endpoint = "http://{}:{}".format(pacs_host, pacs_port)
        self.delete_complete_study = delete_complete_study

        super().__init__(
            dag,
            name='delete-pacs',
            python_callable=self.start,
            *args, **kwargs
        )
