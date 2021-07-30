import os
import time
import json
import requests

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator, rest_self_udpate
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class ShutdownNodeOperator(KaapanaPythonBaseOperator):

    @rest_self_udpate
    def start(self, ds, ti, **kwargs):

        helm_api = 'http://kube-helm-service.kube-system.svc:5000/kube-helm-api'

        url = '{}/helm-delete-chart?release_name={}'.format(helm_api, self.release_name)
        r =requests.get(url)

        print(
            'Shutting down Openined PySyft-Node',
            'Url: {}'.format(url),
            'Repsonse: {}'.format(r.text),
            sep='\n'
        )


    def __init__(
        self,
        dag,
        release_name,
        *args,**kwargs):

        self.release_name = release_name

        super().__init__(
            dag,
            name='shutdown-node',
            python_callable=self.start,
            *args, **kwargs
        )
