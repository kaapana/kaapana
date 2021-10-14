
from minio import Minio
import os
import glob
import uuid
import json
import datetime
from datetime import timedelta

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator, rest_self_udpate
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from kaapana.blueprints.kaapana_utils import generate_minio_credentials
from kaapana.operators.HelperMinio import HelperMinio

class LocalCreateStudyIDJsonOperator(KaapanaPythonBaseOperator):

    @rest_self_udpate
    def start(self, ds, **kwargs):
        conf = kwargs['dag_run'].conf
        print('conf', conf)
        if 'conf' in conf and 'form_data' in conf['conf'] and conf['conf']['form_data'] is not None and 'zip_files' in conf['conf']['form_data']:
                self.zip_files = conf['conf']['form_data']['zip_files']
                print('Zip files set by form data', self.zip_files)

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]
        print(batch_folder)

        to_be_uploaded = []
        for batch_element_dir in batch_folder:
            metadata_json = os.path.join(batch_element_dir, self.operator_in_dir, 'metadata.json')
            print(metadata_json)
            with open(metadata_json) as f:
                data = json.load(f)
                to_be_uploaded.append({
                    "text": f'study-id-{data["0020000D StudyInstanceUID_keyword"]}'
                })            
        
        print(to_be_uploaded)
        
        batch_output_dir = os.path.join(run_dir, self.operator_out_dir)
        if not os.path.exists(batch_output_dir):
            os.makedirs(batch_output_dir)
        
        with open(os.path.join(batch_output_dir, 'study_ids.json'), 'w') as f:
            json.dump(to_be_uploaded, f)

        return

    def __init__(self,
        dag,
        name='create-study-id-json',
        *args, **kwargs
        ):
    
        super().__init__(
           dag,
           name=name,
           python_callable=self.start,
           execution_timeout=timedelta(minutes=30),
           *args,
           **kwargs
        )