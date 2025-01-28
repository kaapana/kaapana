from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class ExternalPacsOperator(KaapanaBaseOperator):
    def __init__(self, dag, execution_timeout=timedelta(minutes=120), **kwargs):
        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/external-pacs:{KAAPANA_BUILD_VERSION}",
            name="external-pacs",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            **kwargs,
        )
