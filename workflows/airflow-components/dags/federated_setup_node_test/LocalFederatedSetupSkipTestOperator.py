
from minio import Minio
import os
import glob
import uuid
import json
from zipfile import ZipFile
import datetime
from datetime import timedelta

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator, rest_self_udpate
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from kaapana.blueprints.kaapana_utils import generate_minio_credentials
from kaapana.operators.HelperMinio import HelperMinio
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.HelperFederated import federated_sharing_decorator

class LocalFederatedSetupSkipTestOperator(KaapanaPythonBaseOperator):

    @federated_sharing_decorator
    @cache_operator_output
    @rest_self_udpate
    def start(self, ds, **kwargs):
        conf = kwargs['dag_run'].conf
        print('conf', conf)
        return

    def __init__(self,
        dag,
        **kwargs
        ):

        super(LocalFederatedSetupSkipTestOperator, self).__init__(
           dag=dag,
           name=f'federated-setup-skip-test',
           python_callable=self.start,
           execution_timeout=timedelta(minutes=30),
           **kwargs
        )