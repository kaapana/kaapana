
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

class LocalDevOperator(KaapanaPythonBaseOperator):

    @federated_sharing_decorator
    @cache_operator_output
    @rest_self_udpate
    def start(self, ds, **kwargs):
        conf = kwargs['dag_run'].conf
        print('conf', conf)
        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]


        json_output_path=os.path.join(run_dir, self.operator_out_dir, "model.json")
        if not os.path.exists(os.path.dirname(json_output_path)):
            os.makedirs(os.path.dirname(json_output_path))
        if os.path.isfile(json_output_path):
            with open(json_output_path, "r", encoding='utf-8') as jsonData:
                model = json.load(jsonData)
        else:
            model = {'epochs': [0]}
        with open(json_output_path, "w", encoding='utf-8') as jsonData:
            model['epochs'].append(model['epochs'][-1] + 1)
            json.dump(model, jsonData, indent=4, sort_keys=True, ensure_ascii=True)
        return

    def __init__(self,
        dag,
        **kwargs
        ):

        super(LocalDevOperator, self).__init__(
           dag=dag,
           name=f'local-dev',
           python_callable=self.start,
           allow_federated_learning=True,
           execution_timeout=timedelta(minutes=30),
           **kwargs
        )