from datetime import timedelta

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class CustomNotifyOperator(KaapanaBaseOperator):
    def __init__(
        self,
        dag,
        name="custom-notify",
        execution_timeout=timedelta(seconds=30),
        *args,
        **kwargs,
    ):
        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/custom-notify:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            *args,
            **kwargs,
        )
