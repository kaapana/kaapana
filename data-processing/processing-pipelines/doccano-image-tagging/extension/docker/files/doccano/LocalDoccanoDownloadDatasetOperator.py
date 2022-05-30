import os
import glob
import json
import datetime
import time
import requests
import pandas as pd
from io import StringIO

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from kaapana.operators.HelperCaching import cache_operator_output

class LocalDoccanoDownloadDatasetOperator(KaapanaPythonBaseOperator):

    @cache_operator_output
    def start(self, ds, **kwargs):
        print("Starting moule LocalNLPDownloadProjectOperator...")
        print(kwargs)

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        conf = kwargs['dag_run'].conf
        print(conf)
        project_number = conf['project_id']
        print(project_number)

        DOCCANO_API = 'http://doccano-backend-service.store:8000/v1/'

        # Login
        url = DOCCANO_API + 'auth/login/'
        payload = {'username': 'doccanoadmin', 'password': 'doccano123'} # if password was set via the django api
        r = requests.post(url, data=payload)
        print(r.raise_for_status())
        print(r)
        print(r.json())
        token = r.json()['key']
        headers = {
            'Authorization': 'Token ' + token,
        }
        
        # Downloading
        def download_prepare(download):
            url = DOCCANO_API + f'tasks/status/{download["task_id"]}'
            r = requests.get(url, headers=headers)
            return r.json()['ready']

        def download_url(url, save_path, headers, chunk_size=128):
            r = requests.get(url, stream=True, headers=headers)
            with open(save_path, 'wb') as fd:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    fd.write(chunk)

        data = {"format":"JSON","exportApproved": False}
        url = DOCCANO_API + f'projects/{project_number}/download'
        r = requests.post(url, json=data, headers=headers)
        download = r.json()

        download_status = False
        for idx in range(100):
            time.sleep(1)
            download_status = download_prepare(download)
            if download_status is True:
                break
        print(f'Donwload prepared after {idx} seconds')
      
        batch_output_dir = os.path.join(run_dir, self.operator_out_dir)  # , project_name)
        if not os.path.exists(batch_output_dir):
            os.makedirs(batch_output_dir)

        url = DOCCANO_API + f'projects/{project_number}/download?taskId={download["task_id"]}'
        download_url(url, os.path.join(batch_output_dir, 'data.zip'), headers)

    def __init__(self,
                dag,
                name="doccano-download-dataset",
                *args, **kwargs):

        super().__init__(
            dag=dag,
            name=name,
            python_callable=self.start,
            *args, **kwargs
        )
