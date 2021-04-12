import os
import json
import requests

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator, rest_self_udpate
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

class TriggerDagOperator(KaapanaPythonBaseOperator):
    
    @rest_self_udpate
    def start(self, ds, **kwargs):
        
        if self.rest_call is None:
            raise AssertionError('A corresponding rest call for the dag must be provided!')

        if self.dag_host is None:
            url = f'http://airflow-service.flow.svc:8080/flow/kaapana/api/trigger/{self.dag_name}'
        else:
            url = f'https://{self.dag_host}/flow/kaapana/api/trigger/{self.dag_name}'

        print('Calling DAG: {}'.format(url))
        print('REST CALL: ', json.dumps(self.rest_call, indent=4))

        r = requests.post(url, json=self.rest_call, verify=False)
        print(r.json())


    def __init__(self,
                 dag,
                 dag_host=None,
                 dag_name=None,
                 rest_call=None,
                 clean_workflow_dir=True,
                 *args, **kwargs):
        
        self.dag_host=dag_host
        self.dag_name=dag_name
        self.rest_call=rest_call

        super().__init__(
            dag,
            name=f'trigger-dag',
            python_callable=self.start,
            *args, **kwargs
        )
