from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class Statistics2PdfOperator(KaapanaBaseOperator):
    def __init__(self, dag, execution_timeout=timedelta(minutes=10), **kwargs):
        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/statistics2pdf:{KAAPANA_BUILD_VERSION}",
            name="stats2pdf",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            **kwargs,
        )
