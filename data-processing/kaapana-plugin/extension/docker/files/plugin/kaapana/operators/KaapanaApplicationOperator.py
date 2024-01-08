import os
import shutil
import glob
import time
import secrets
import json
import requests
from airflow.exceptions import AirflowException
from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    PROCESSING_WORKFLOW_DIR,
    ADMIN_NAMESPACE,
    SERVICES_NAMESPACE,
    JOBS_NAMESPACE,
)
from kaapana.blueprints.kaapana_utils import cure_invalid_name, get_release_name


class KaapanaApplicationOperator(KaapanaPythonBaseOperator):
    HELM_API = f"http://kube-helm-service.{ADMIN_NAMESPACE}.svc:5000"
    TIMEOUT = 60 * 60 * 12

    def start(self, ds, **kwargs):
        print(kwargs)
        release_name = (
            get_release_name(kwargs) if self.release_name is None else self.release_name
        )

        dynamic_volumes_dict = {
            "af-data-jobs": PROCESSING_WORKFLOW_DIR,
            "minio-jobs": "/minio",
            "mounted-scripts-jobs": "/kaapana/mounted/workflows/mounted_scripts",
        }

        dynamic_volumes = {}
        for idx, (name, mount_path) in enumerate(dynamic_volumes_dict.items()):
            dynamic_volumes.update(
                {
                    f"global.dynamicVolumes[{idx}].name": name,
                    f"global.dynamicVolumes[{idx}].mount_path": mount_path,
                }
            )

        payload = {
            "name": f"{self.chart_name}",
            "version": self.version,
            "release_name": release_name,
            "sets": {
                "global.namespace": JOBS_NAMESPACE,
                **dynamic_volumes,
                "mount_path": f'{self.data_dir}/{kwargs["run_id"]}',
                "workflow_dir": f'{str(PROCESSING_WORKFLOW_DIR)}/{kwargs["run_id"]}',
                "batch_name": str(self.batch_name),
                "operator_out_dir": str(self.operator_out_dir),
                "operator_in_dir": str(self.operator_in_dir),
                "batches_input_dir": f'{str(PROCESSING_WORKFLOW_DIR)}/{kwargs["run_id"]}/{self.batch_name}',
            },
        }

        conf = kwargs["dag_run"].conf

        if "form_data" in conf:
            form_data = conf["form_data"]
            if "annotator" in form_data:
                payload["sets"]["annotator"] = form_data["annotator"]

        for set_key, set_value in self.sets.items():
            payload["sets"][set_key] = set_value

        url = f"{KaapanaApplicationOperator.HELM_API}/helm-install-chart"

        print("payload")
        print(payload)
        r = requests.post(url, json=payload)
        print(r)
        print(r.text)
        r.raise_for_status()

        t_end = time.time() + KaapanaApplicationOperator.TIMEOUT
        while time.time() < t_end:
            time.sleep(15)
            url = f"{KaapanaApplicationOperator.HELM_API}/view-chart-status"
            r = requests.get(url, params={"release_name": release_name})
            if r.status_code == 500 or r.status_code == 404:
                print(f"Release {release_name} was uninstalled. My job is done here!")
                break
            r.raise_for_status()

    @staticmethod
    def uninstall_helm_chart(kwargs):
        release_name = get_release_name(kwargs)
        url = f"{KaapanaApplicationOperator.HELM_API}/helm-delete-chart"
        r = requests.post(url, params={"release_name": release_name})
        r.raise_for_status()
        print(r)
        print(r.text)

    @staticmethod
    def on_failure(context):
        """
        Use this method with caution, because it unclear at which state the context object is updated!
        """
        print("##################################################### ON FAILURE!")

    @staticmethod
    def on_retry(context):
        """
        Use this method with caution, because it unclear at which state the context object is updated!
        """
        print("##################################################### ON RETRY!")

    def __init__(
        self,
        dag,
        chart_name,
        version,
        name="helm-chart",
        data_dir=None,
        sets=None,
        release_name=None,
        **kwargs,
    ):
        self.chart_name = chart_name
        self.version = version

        self.sets = sets or dict()
        self.data_dir = data_dir or os.getenv("DATADIR", "")
        self.release_name = release_name

        super().__init__(
            dag=dag,
            name=name,
            python_callable=self.start,
            execution_timeout=timedelta(seconds=KaapanaApplicationOperator.TIMEOUT),
            **kwargs,
        )
