from datetime import timedelta

import requests
from airflow.exceptions import AirflowSkipException
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
    PLATFORM_PREFIX,
    SERVICES_NAMESPACE,
)

class CleanUpExpiredWorkflowDataOperator(KaapanaBaseOperator):
    """
    Operator to cleanup/remove the expired workflows data directories

    **Inputs:**

    * expired_period: Clean items that have expired since a certain period.

    """
    def __init__(self, dag, expired_period=timedelta(days=60), env_vars=None, **kwargs):
        """
        :param dag: DAG in which the operator has to be executed.
        :param expired_period: Clean items that have expired since in day(s), default: 60 days
        """



        if env_vars is None:
            env_vars = {}

        envs = {
            "EXPIRED_PERIOD": str(int(expired_period.total_seconds())),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/cleanup-expired-workflows:{KAAPANA_BUILD_VERSION}",
            name="clean-up",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            **kwargs,
        )

    def pre_execute(self, context):
        # The DAG lists the namespaces once when its run starts. A project deleted
        # since then has nothing left to clean, and its namespace is gone or being
        # deleted, so a pod started there would only fail or hang. Checked here, not
        # in execute: Airflow warns when an overridden execute calls super().execute.
        super().pre_execute(context)
        if self.namespace and self.namespace.startswith(f"{PLATFORM_PREFIX}-project-"):
            response = requests.get(
                f"http://aii-service.{SERVICES_NAMESPACE}.svc:8080/projects", timeout=5
            )
            response.raise_for_status()
            if self.namespace not in {
                p["kubernetes_namespace"] for p in response.json()
            }:
                raise AirflowSkipException(
                    f"No project owns namespace {self.namespace} any more, "
                    "nothing to clean up"
                )
