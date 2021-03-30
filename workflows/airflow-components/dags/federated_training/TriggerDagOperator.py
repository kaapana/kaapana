import os
import json
import requests

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator, rest_self_udpate


class TriggerDagOperator(KaapanaPythonBaseOperator):
    
    @rest_self_udpate
    def start(self, ds, **kwargs):

        if self.dag_host is None:
            url = 'http://airflow-service.flow.svc:8080/flow/kaapana/api/trigger/{}'.format(self.dag_name)
        else:
            url = 'https://{}/flow/kaapana/api/trigger/{}'.format(self.dag_host, self.dag_name)

        print('Calling DAG: {}'.format(url))
        print('Rest call: {}'.format(self.rest_call))

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
        
        location = 'local' if dag_host is None else 'remote'

        super().__init__(
            dag,
            name=f'trigger-{location}-dag',
            python_callable=self.start,
            *args, **kwargs
        )
