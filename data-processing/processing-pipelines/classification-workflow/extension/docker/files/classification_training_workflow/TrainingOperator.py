from datetime import timedelta

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class TrainingOperator(KaapanaBaseOperator):
    def __init__(
        self,
        dag,
        name="classification-training",
        execution_timeout=timedelta(minutes=20),
        *args,
        **kwargs,
    ):
        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/classification-training:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=16000,
            gpu_mem_mb=11000,
            labels={"network-access": "opensearch"},
            *args,
            **kwargs,
        )
