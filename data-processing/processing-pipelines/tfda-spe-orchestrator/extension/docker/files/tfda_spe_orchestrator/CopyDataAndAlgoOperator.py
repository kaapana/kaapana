from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class CopyDataAndAlgoOperator(KaapanaBaseOperator):
    """
    Operator for copying data and algorithm files into the Secure Processing Environment (SPE).

    This operator extends the KaapanaBaseOperator and is designed to facilitate the copying of user
    selected data and algorithm files into the Secure Processing Environment (SPE) by triggering the respective
    processing container. It is intended to be used within the Kaapana platform and makes use of specific
    Kaapana variables and configurations.

    Notes:
        1. Ensure that the environment variable called "TASK_TYPE" is passed on with the name of the operator task.
    """

    execution_timeout = timedelta(hours=10)

    def __init__(
        self,
        dag,
        name="copy-data-algo",
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
