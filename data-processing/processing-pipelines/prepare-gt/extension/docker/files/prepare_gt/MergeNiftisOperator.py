from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class MergeNiftisOperator(KaapanaBaseOperator):
    def __init__(
        self,
        dag,
        mask_operator,
        parameters="--all-features",
        log_level="INFO",
        env_vars=None,
        execution_timeout=timedelta(minutes=120),
        **kwargs,
    ):
        if env_vars is None:
            env_vars = {}

        envs = {
            "LOG_LEVEL": str(log_level),
        }

        env_vars.update(envs)
        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/merge-niftis:{KAAPANA_BUILD_VERSION}",
            name="radiomics",
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=5000,
            **kwargs,
        )
