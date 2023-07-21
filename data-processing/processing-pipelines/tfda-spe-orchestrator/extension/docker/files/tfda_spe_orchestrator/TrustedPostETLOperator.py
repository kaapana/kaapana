from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class TrustedPostETLOperator(KaapanaBaseOperator):
    """
    Operator for running post-processing on the results of the execution of workflows inside the Secure Processing Environment (SPE).

    This operator is currently only a placeholder and in future will support post-processing security
    measures on the results of the workflows that were run inside the SPE. It is intended to be used
    within the Kaapana platform and makes use of specific Kaapana variables and configurations.

    Notes:
        1. Ensure that the environment variable called "TASK_TYPE" is passed on with the name of the operator task.
    """

    execution_timeout = timedelta(hours=10)

    def __init__(
        self,
        dag,
        name="trusted-post-etl",
        env_vars={},
        execution_timeout=execution_timeout,
        **kwargs,
    ):
        envs = {"ETL_STAGE": "post"}
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/pre-and-post-etl:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            **kwargs,
        )
