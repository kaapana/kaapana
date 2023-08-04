from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class NnUnetModelOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(minutes=10)

    def __init__(
        self,
        dag,
        name="model-management",
        target_level="default",
        execution_timeout=execution_timeout,
        **kwargs,
    ):
        envs = {
            "TARGET_LEVEL": str(target_level),
        }

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/nnunet-model-management:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=1000,
            env_vars=envs,
            **kwargs,
        )
