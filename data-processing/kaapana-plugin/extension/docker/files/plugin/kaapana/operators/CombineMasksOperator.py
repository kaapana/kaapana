from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class CombineMasksOperator(KaapanaBaseOperator):
    """
    Searches for NIFTI files (expects segmentation masks) in oeprator input-dir and combines them into a single NIFTI-file.
    """

    execution_timeout = timedelta(minutes=60)

    def __init__(
        self,
        dag,
        name="combine-masks",
        env_vars=None,
        execution_timeout=execution_timeout,
        **kwargs,
    ):
        ram_mem_mb = 8000
        gpu_mem_mb = None

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/combine-masks:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            keep_parallel_id=False,
            enable_proxy=True,
            env_vars=env_vars,
            ram_mem_mb=ram_mem_mb,
            gpu_mem_mb=gpu_mem_mb,
            **kwargs,
        )
