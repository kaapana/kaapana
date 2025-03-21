from kaapana.operators.KaapanaBaseOperator import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
    KaapanaBaseOperator,
)
from datetime import timedelta


class CheckCompletenessOperator(KaapanaBaseOperator):
    def __init__(self, dag, env_vars=None, **kwargs):
        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/check-completeness:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=timedelta(minutes=15),
            ram_mem_mb=4000,
            ram_mem_mb_lmt=8000,
            **kwargs,
        )
