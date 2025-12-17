import shutil
from pathlib import Path
from kaapana.blueprints.kaapana_utils import (
    get_operator_properties,
    clean_previous_dag_run,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    SERVICES_NAMESPACE,
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
    AIRFLOW_WORKFLOW_DIR,
)

from kubernetes import client
from kubernetes.client.exceptions import ApiException


class LocalWorkflowCleanerOperator(KaapanaBaseOperator):
    """
    Cleans a workflow dir.

    Cleans a  workflow and optionally deleting the workflow directory.
    This is not a local operator anymore.

    """

    def delete_conf_configmap(self, configmap_name: str, namespace: str):
        """
        Delete a ConfigMap by name in the given namespace.
        This is locally executed in airflow after workflow cleanup
        """
        v1 = client.CoreV1Api()
        try:
            v1.delete_namespaced_config_map(
                name=configmap_name,
                namespace=namespace,
            )
            print(f"Deleted ConfigMap: {configmap_name}")
        except ApiException as e:
            # 404 = Already deleted or never existed
            if e.status == 404:
                print(f"ConfigMap {configmap_name} not found — nothing to delete.")
            else:
                raise

    def post_execute(self, context, result=None):
        run_id = context["run_id"]
        configmap_name = f"{run_id}-config"
        namespace = self.namespace
        self.delete_conf_configmap(configmap_name, namespace)

        conf = context["dag_run"].conf or {}
        # federed workflows run in SERVICES_NAMESPACE, so the cleanup can also be local only
        clean_previous_dag_run(self.airflow_workflow_dir, conf, "from_previous_dag_run")
        clean_previous_dag_run(
            self.airflow_workflow_dir, conf, "before_previous_dag_run"
        )

        run_dir = Path(AIRFLOW_WORKFLOW_DIR, run_id)
        # removes task_run_files created locally
        if self.clean_workflow_dir and Path(run_dir).exists():
            print(("Cleaning dir: %s in SERVICES_NAMESPACE" % run_dir))
            shutil.rmtree(run_dir)

    def __init__(self, dag, clean_workflow_dir: bool = True, **kwargs):
        """
        :param clean_workflow_dir: Bool if workflow directory should be deleted
        """
        envs = {"CLEAN_WORKFLOW_DIR": str(clean_workflow_dir)}
        self.clean_workflow_dir = clean_workflow_dir

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/workflow-cleaner:{KAAPANA_BUILD_VERSION}",
            name="workflow-cleaner",
            image_pull_secrets=["registry-secret"],
            env_vars=envs,
            **kwargs,
        )
