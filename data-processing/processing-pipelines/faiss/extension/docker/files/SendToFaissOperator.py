from datetime import timedelta

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class SendToFaissOperator(KaapanaBaseOperator):
    def __init__(
        self,
        dag,
        name="send-to-faiss",
        execution_timeout=timedelta(minutes=20),
        *args,
        **kwargs,
    ):
        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/send-to-faiss:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=16000,
            gpu_mem_mb=11000,
            labels={"network-access": "faiss"},
            *args,
            **kwargs,
        )
