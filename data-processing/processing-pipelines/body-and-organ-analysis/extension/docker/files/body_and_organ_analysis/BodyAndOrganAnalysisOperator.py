from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class BodyAndOrganAnalysisOperator(KaapanaBaseOperator):
    """
    Start an Airflow task that executes the body-and-organ-analysis on nifti files.
    """

    execution_timeout = timedelta(minutes=600)
    task_dict = {}

    def __init__(
        self,
        dag,
        env_vars={},
        parallel_id=None,
        execution_timeout=execution_timeout,
        **kwargs,
    ):
        if "labels" not in kwargs or not isinstance(kwargs["labels"], dict):
            kwargs["labels"] = {}
        kwargs["labels"]["network-access-external-ips"] = "true"
        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/body-and-organ-analysis:{KAAPANA_BUILD_VERSION}",
            name="body-and-organ-analysis",
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=24000,
            ram_mem_mb_lmt=25000,
            gpu_mem_mb=11000,
            env_vars=env_vars,
            enable_proxy=True,
            **kwargs,
        )
