import os
import time
from datetime import timedelta

import requests
from kaapana.blueprints.kaapana_global_variables import (
    ADMIN_NAMESPACE,
    PROCESSING_WORKFLOW_DIR,
)
from kaapana.blueprints.kaapana_utils import cure_invalid_name, get_release_name
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class KaapanaApplicationOperator(KaapanaPythonBaseOperator):
    """
    A custom Airflow operator for deploying and managing Helm charts within the Kaapana framework.
    """

    HELM_API = f"http://kube-helm-service.{ADMIN_NAMESPACE}.svc:5000"
    TIMEOUT = 60 * 60 * 12

    def start(self, ds, **kwargs):
        print(kwargs)
        conf = kwargs["dag_run"].conf
        release_name = (
            get_release_name(kwargs) if self.release_name is None else self.release_name
        )

        try:
            project_form = conf.get("project_form")
            self.namespace = project_form.get("kubernetes_namespace")
        except (KeyError, AttributeError):
            self.namespace = "project-admin"

        dynamic_volumes_dict = {
            f"{self.namespace}-workflow-data": PROCESSING_WORKFLOW_DIR,
            f"{self.namespace}-mounted-scripts": "/kaapana/mounted/workflows/mounted_scripts",
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
                "global.namespace": self.namespace,
                "global.project_namespace": self.namespace,
                "global.project_name": project_form.get("name"),
                **dynamic_volumes,
                "mount_path": f'{self.data_dir}/{kwargs["run_id"]}',
                "workflow_dir": f'{str(PROCESSING_WORKFLOW_DIR)}/{kwargs["run_id"]}',
                "batch_name": str(self.batch_name),
                "operator_out_dir": str(self.operator_out_dir),
                "operator_in_dir": str(self.operator_in_dir),
                "batches_input_dir": f'{str(PROCESSING_WORKFLOW_DIR)}/{kwargs["run_id"]}/{self.batch_name}',
            },
        }

        if "workflow_form" in conf:
            workflow_form = conf["workflow_form"]
            if "annotator" in workflow_form:
                payload["sets"]["annotator"] = workflow_form["annotator"]

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
        """
        :param dag (airflow.models.DAG): The DAG object to which the operator belongs.
        :param chart_name (str): The name of the Helm chart to be deployed.
        :param version (str): The version of the Helm chart to be deployed.
        :param name (str): The name of the operator task (default: "helm-chart").
        :param data_dir (str, optional): The directory for storing workflow-specific data (default: `DATADIR` environment variable).
        :param sets (dict, optional): Additional key-value pairs to be included in the Helm chart configuration.
        :param release_name (str, optional): The release name for the Helm deployment (default: generated dynamically).
        :param kwargs: Additional arguments passed to the `KaapanaPythonBaseOperator` constructor.
        """
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
