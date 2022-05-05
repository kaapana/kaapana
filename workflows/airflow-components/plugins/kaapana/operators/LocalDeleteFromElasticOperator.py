import glob
import os
from datetime import timedelta
from urllib.error import URLError, HTTPError
import urllib.request
from elasticsearch import Elasticsearch
import pydicom
import requests
import time
import json

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalDeleteFromElasticOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):
        conf = kwargs['dag_run'].conf
        if 'conf' in conf and 'form_data' in conf['conf'] and conf['conf']['form_data'] is not None and 'delete_complete_study' in conf['conf']['form_data']:
                self.delete_complete_study = conf['conf']['form_data']['delete_complete_study']
                print('Delete entire study set to ', self.delete_complete_study)
        self.es = Elasticsearch([{'host': self.elastic_host, 'port': self.elastic_port}])
        if self.delete_all_documents:
            print("Delting all documents from elasticsearch...")
            query = {"query": {"match_all": {}}}
            self.delete_by_query(query)
        else:
            run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
            batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]

            dicoms_to_delete = []
            for batch_element_dir in batch_folder:
                dcm_files = sorted(glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.dcm*"), recursive=True))
                if len(dcm_files) > 0:
                    incoming_dcm = pydicom.dcmread(dcm_files[0])
                    series_uid = incoming_dcm.SeriesInstanceUID
                    study_uid = incoming_dcm.StudyInstanceUID
                    if self.delete_complete_study:
                        dicoms_to_delete.append(study_uid)
                    else:
                        dicoms_to_delete.append(series_uid)
                else:
                    json_files = sorted(glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.json*"), recursive=True))
                    for meta_files in json_files:
                        with open(meta_files) as fs:
                            metadata = json.load(fs)
                            dicoms_to_delete.append({
                                'study_uid': metadata['0020000D StudyInstanceUID_keyword'],
                                'series_uid':  metadata['0020000E SeriesInstanceUID_keyword']
                        })

            if self.delete_complete_study:
                query = {"query": {"terms": {"0020000D StudyInstanceUID_keyword": dicoms_to_delete}}}
            else:
                query = {"query": {"terms": {"_id": dicoms_to_delete}}}

            self.delete_by_query(query)

    def delete_by_query(self, query):
        try:
            res = self.es.delete_by_query(index=self.elastic_index, body=query)
            print(res)
        except Exception as e:
            print("ERROR deleting from elasticsearch: {}".format(str(e)))
            raise ValueError('ERROR')

    def __init__(self,
                 dag,
                 delete_operator=None,
                 elastic_host='elastic-meta-service.meta.svc',
                 elastic_port=9200,
                 elastic_index="meta-index",
                 delete_all_documents=False,
                 delete_complete_study=False,
                 **kwargs):

        self.elastic_host = elastic_host
        self.elastic_port = elastic_port
        self.elastic_index = elastic_index
        self.delete_all_documents = delete_all_documents
        self.delete_complete_study = delete_complete_study

        super().__init__(
            dag=dag,
            name='delete-meta',
            python_callable=self.start,
            **kwargs
        )
