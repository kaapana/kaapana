
from minio import Minio
import os
import glob
import uuid
import json
import datetime
from datetime import timedelta
import requests

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator, rest_self_udpate
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from kaapana.blueprints.kaapana_utils import generate_minio_credentials
from kaapana.operators.HelperMinio import HelperMinio
from kaapana.operators.HelperCaching import cache_operator_output

DOCCANO_API = 'http://doccano-backend-service.store:8000/v1/'

class LocalDoccanoUploadDatasetOperator(KaapanaPythonBaseOperator):

    @cache_operator_output
    @rest_self_udpate
    def start(self, ds, **kwargs):
        conf = kwargs['dag_run'].conf

        if 'workflow_form' in conf and conf['workflow_form'] is not None:
            project_payload = conf['workflow_form']

        print('project_payload', project_payload)

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_input_dir = os.path.join(run_dir, self.operator_in_dir)     

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

        # Project creation
        url = DOCCANO_API + 'projects'
        project_payload.update({
            "random_order":False,
            "collaborative_annotation":False,
            "single_class_classification":False,
            "resourcetype":"TextClassificationProject"
        })

        if project_payload['project_type'] == 'DocumentClassification':
            project_payload['resourcetype'] = 'TextClassificationProject'
        elif project_payload['project_type'] == 'Seq2seq':
            project_payload['resourcetype'] = 'Seq2seqProject'
        else:
            raise NameError('resource type not specified!')

        r = requests.post(url, data=project_payload, headers=headers)
        print(r)
        print(r.content)
        print(r.raise_for_status())
        project = r.json()
        print(project['id'])
        project_number = str(project['id'])

        # Uploading
        url = DOCCANO_API + 'fp/process/'
        filename = 'study_ids.json'
        files = {'filepond': (filename, open(os.path.join(batch_input_dir, filename)), 'multipart/form-data')}

        print(headers)
        r = requests.post(url, files=files, headers=headers)
        print(r.raise_for_status())
        upload_id = r.text
        print(upload_id)
        url = DOCCANO_API + f'projects/{project_number}/upload'
        print(url)
        payload = {"format":"JSON","uploadIds":[upload_id],"column_data":"text","column_label":"label","delimiter":"","encoding":"utf_8"}
        r = requests.post(url, json=payload, headers=headers)
        print(r.raise_for_status())
        print(r.text)

        return

    def __init__(self,
        dag,
        name='doccano-upload',
        *args, **kwargs
        ):
    
        super().__init__(
           dag=dag,
           name=name,
           python_callable=self.start,
           execution_timeout=timedelta(minutes=30),
           *args,
           **kwargs
        )