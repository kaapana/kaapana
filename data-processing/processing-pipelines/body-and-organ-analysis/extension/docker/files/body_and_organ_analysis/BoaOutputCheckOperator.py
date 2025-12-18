from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class BoaOutputCheckOperator(KaapanaBaseOperator):
    def __init__(
        self,
        dag,
        name="boa-output-check-operator",
        parallel_id=None,
        execution_timeout=timedelta(minutes=20),
        *args,
        **kwargs,
    ):
        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/boa-output-check:{KAAPANA_BUILD_VERSION}",
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=1000,
            ram_mem_mb_lmt=3000,
            *args,
            **kwargs,
        )
