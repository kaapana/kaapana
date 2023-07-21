from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class FetchResultsOperator(KaapanaBaseOperator):
    """
    Fetches results from the Secure Processing Environment (SPE).

    This operator extends the KaapanaBaseOperator and allows fetching of the analysis results from the
    SPE for further processing by triggering the respective processing container. It is intended to be
    used within the Kaapana platform and makes use of specific Kaapana variables and configurations.
    """

    execution_timeout = timedelta(hours=10)

    def __init__(
        self,
        dag,
        name="fetch-results",
        env_vars={},
        execution_timeout=execution_timeout,
        **kwargs,
    ):
        envs = {"TASK_TYPE": name}
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/trigger-ansible-playbook:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            **kwargs,
        )
