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

    Attributes:
        HELM_API (str): The base URL for the Helm API service within the Kubernetes cluster.
        TIMEOUT (int): The timeout duration (in seconds) for the Helm chart deployment process.

    Methods:
        start(ds, **kwargs):
            Deploys a Helm chart based on the provided configurations in the Airflow DAG run context.
            Handles namespace selection, dynamic volume allocation, and additional configuration
            settings. Monitors the status of the deployment until it completes or times out.

        uninstall_helm_chart(kwargs):
            Uninstalls the Helm release corresponding to the given release name using the Helm API.

        on_failure(context):
            Triggered when the operator fails. Logs a failure message.
            (Use with caution due to unclear state of the context object during execution.)

        on_retry(context):
            Triggered when the operator is retried. Logs a retry message.
            (Use with caution due to unclear state of the context object during execution.)

    Args:
        dag (airflow.models.DAG): The DAG object to which the operator belongs.
        chart_name (str): The name of the Helm chart to be deployed.
        version (str): The version of the Helm chart to be deployed.
        name (str): The name of the operator task (default: "helm-chart").
        data_dir (str, optional): The directory for storing workflow-specific data (default: `DATADIR` environment variable).
        sets (dict, optional): Additional key-value pairs to be included in the Helm chart configuration.
        release_name (str, optional): The release name for the Helm deployment (default: generated dynamically).
        **kwargs: Additional arguments passed to the `KaapanaPythonBaseOperator` constructor.

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
