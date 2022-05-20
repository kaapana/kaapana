
import os
import time
import glob
from datetime import timedelta
from datetime import datetime
import requests
import shutil

from airflow.models.dagbag import DagBag

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import WORKFLOW_DIR


class LocalServiceSyncDagsDbOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):
        conf = kwargs['dag_run'].conf

        tries = 0
        max_tries = 4
        success = False

        AIRFLOW_API = 'http://airflow-service.flow.svc:8080/'
        url = f"{AIRFLOW_API}flow/kaapana/api/getdags"
        while not success and tries < max_tries:
            tries += 1
            try:
                r = requests.get(url, timeout=1)
                success = True
            except:
                print(f"Connections issue: {url}")
                success = False

        if tries >= max_tries:
            print(f"Could not connect to: {url}")
            exit(1)

        db_dags = []
        for key, value in r.json().items():
            db_dags.append(value['dag_id'])
        print('db', db_dags)

        airflow_home = os.environ.get('AIRFLOW_HOME')
        dagbag = DagBag(os.path.join(airflow_home, 'dags'))

        file_dags = []
        for key, dag in dagbag.dags.items():
            file_dags.append(dag.dag_id)
        print(f"{file_dags=}")

        dags_to_delete = [item for item in db_dags if item not in file_dags]
        print(f"{dags_to_delete=}")
        for dag_id in dags_to_delete:
            print('Deleting', dag_id)
            r = requests.delete(f'{AIRFLOW_API}flow/api/experimental/dags/{dag_id}')
            print(r.status_code)
            print(r.text)

        return

    def __init__(self,
                 dag,
                 expired_period=timedelta(days=60),
                 **kwargs
                 ):

        self.expired_period = expired_period

        super().__init__(
            dag=dag,
            name=f'remove-deleted-dags-from-db',
            python_callable=self.start,
            **kwargs
        )
