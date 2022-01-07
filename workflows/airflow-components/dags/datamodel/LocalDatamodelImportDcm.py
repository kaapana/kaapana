import os
import glob
import json
import datetime
import requests

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

class LocalDatamodelImportDcm(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):
        print("Starting moule LocalDatamodelImportDcm...")
        
        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_dirs = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]
        
        for batch_element_dir in batch_dirs:
            dcm_files = sorted(glob.glob(os.path.join(batch_element_dir, self.operator_in_dir,"*.dcm*"),recursive=True))
            data = {"files" : dcm_files }
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
            #TODO: add auth
            r = requests.post(self.url, data=json.dumps(data), headers=headers)
            if r.status_code != 200:
                print("Error response: %s !" % r.status_code)
                print(r.content)  



    def __init__(self,
                 dag,
                 name='datamodel-import-dcm',
                 url='http://datamodel-service.base.svc:5000/api/v1/import_dicom/',
                 **kwargs):
        self.url = url

        super().__init__(
            dag=dag,
            name=name,
            python_callable=self.start,
            **kwargs
        )