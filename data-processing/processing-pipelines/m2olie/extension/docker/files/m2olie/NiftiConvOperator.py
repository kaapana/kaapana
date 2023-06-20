from datetime import timedelta, datetime

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class NiftiConvOperator(KaapanaBaseOperator):
    """
    NiftiConvOperator

    """

    def __init__(
        self,
        dag,
        name: str = "nifti-conv",
        execution_timeout: datetime = timedelta(minutes=60),
        **kwargs,
    ):
        env_vars = {}

        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/example_nifti_conv:{KAAPANA_BUILD_VERSION}",
            ram_mem_mb=5000,
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            # dev_server="code-server",
            **kwargs,
        )
