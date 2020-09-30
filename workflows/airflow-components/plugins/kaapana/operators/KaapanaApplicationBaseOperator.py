import os
import shutil
import glob
import time
import secrets
import requests
from airflow.exceptions import AirflowException
from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from kaapana.blueprints.kaapana_utils import cure_invalid_name

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project


class KaapanaApplicationBaseOperator(KaapanaPythonBaseOperator):
    
    HELM_API='http://kube-helm-service.kube-system.svc:5000/kube-helm-api'
    TIMEOUT = 60*60*12
    
    @staticmethod
    def _get_release_name(kwargs):
        task_id = kwargs['ti'].task_id
        run_id = kwargs['run_id']
        release_name = f'kaapanaint-{run_id}'
        return cure_invalid_name(release_name, r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*", max_length=53)

    def start(self, ds, **kwargs):
        print(kwargs)        
        run_dir = os.path.join(WORKFLOW_DIR, kwargs['run_id'])
        release_name = KaapanaApplicationBaseOperator._get_release_name(kwargs)

        payload={
            'name': f'{self.chart_repo_name}/{self.chart_name}',
            'version': self.version,
            'custom_release_name': release_name,
            'sets': {
                'global.registry_url': 'dktk-jip-registry.dkfz.de',
                'global.registry_project':  '/kaapana',
                'global.base_namespace': 'flow-jobs',
                'global.pull_policy_jobs': 'IfNotPresent',
                'mount_path': f'/home/kaapana/workflows/{run_dir}',
            }
        }

        for set_key, set_value in self.sets.items():
            payload['sets'][set_key] = set_value 

        url = f'{KaapanaApplicationBaseOperator.HELM_API}/helm-install-chart'
        
        print('payload')
        print(payload)
        r = requests.post(url, json=payload)
        print(r)
        print(r.text)
        r.raise_for_status()

        t_end = time.time() + KaapanaApplicationBaseOperator.TIMEOUT
        while time.time() < t_end:
            time.sleep(15)
            url = f'{KaapanaApplicationBaseOperator.HELM_API}/view-chart-status'
            r = requests.get(url, params={'release_name': release_name})
            if r.status_code == 500:
                print(f'Release {release_name} was uninstalled. My job is done here!')
                break
            r.raise_for_status()


    @staticmethod
    def uninstall_helm_chart(kwargs):
        release_name = KaapanaApplicationBaseOperator._get_release_name(kwargs)
        url = f'{KaapanaApplicationBaseOperator.HELM_API}/helm-uninstall-chart'
        r = requests.get(url, params={'release_name': release_name})
        r.raise_for_status()
        print(r)
        print(r.text)

    @staticmethod
    def on_failure(info_dict):
        print("##################################################### ON FAILURE!")
        KaapanaApplicationBaseOperator.uninstall_helm_chart(info_dict)

    @staticmethod
    def on_success(info_dict):
        pass
        
    @staticmethod
    def on_retry(info_dict):
        print("##################################################### ON RETRY!")
        KaapanaApplicationBaseOperator.uninstall_helm_chart(info_dict)

    @staticmethod
    def on_execute(info_dict):
        pass

    def __init__(self,
                 dag,
                 chart_name,
                 version,
                 name="helm-chart",
                 chart_repo_name=None,
                 sets=None,
                 *args, **kwargs):

        self.chart_repo_name = chart_repo_name or 'kaapana-public'
        self.chart_name = chart_name
        self.version = version
        self.sets = sets or dict()

        super().__init__(
            dag=dag,
            name=name,
            python_callable=self.start,
            execution_timeout=timedelta(seconds=KaapanaApplicationBaseOperator.TIMEOUT),
            on_failure_callback=KaapanaApplicationBaseOperator.on_failure,
            on_success_callback=KaapanaApplicationBaseOperator.on_success,
            on_retry_callback=KaapanaApplicationBaseOperator.on_retry,
            on_execute_callback=KaapanaApplicationBaseOperator.on_execute,
            *args, **kwargs
        )


