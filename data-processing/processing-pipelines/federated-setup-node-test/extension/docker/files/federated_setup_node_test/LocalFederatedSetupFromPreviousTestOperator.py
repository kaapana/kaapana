
from minio import Minio
import os
import glob
import uuid
import json
from zipfile import ZipFile
import datetime
from datetime import timedelta

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator, rest_self_udpate
from kaapana.operators.HelperCaching import cache_operator_output

class LocalFederatedSetupFromPreviousTestOperator(KaapanaPythonBaseOperator):

    @cache_operator_output
    @rest_self_udpate
    def start(self, ds, **kwargs):
        conf = kwargs['dag_run'].conf
        print('conf', conf)
        run_dir = os.path.join(self.airflow_workflow_dir, kwargs['dag_run'].run_id)
        json_output_path=os.path.join(run_dir, self.operator_out_dir, "from_previous.json")
        if not os.path.exists(os.path.dirname(json_output_path)):
            os.makedirs(os.path.dirname(json_output_path))
        from_previous = {"let's see if I persist": "yippie"}
        with open(json_output_path, "w", encoding='utf-8') as jsonData:
            json.dump(from_previous, jsonData, indent=4, sort_keys=True, ensure_ascii=True)

        return

    def __init__(self,
        dag,
        **kwargs
        ):

        super(LocalFederatedSetupFromPreviousTestOperator, self).__init__(
           dag=dag,
           name=f'federated-setup-from-previous-test',
           python_callable=self.start,
           execution_timeout=timedelta(minutes=30),
           **kwargs
        )