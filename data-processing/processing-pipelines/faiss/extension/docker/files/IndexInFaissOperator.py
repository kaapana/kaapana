from datetime import timedelta

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class IndexInFaissOperator(KaapanaBaseOperator):
    def __init__(
        self,
        dag,
        name="index-in-faiss",
        execution_timeout=timedelta(minutes=120),
        *args,
        **kwargs,
    ):
        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/index-in-faiss:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=2000,
            *args,
            **kwargs,
        )
