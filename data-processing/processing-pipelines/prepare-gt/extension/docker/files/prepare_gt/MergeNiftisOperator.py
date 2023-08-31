from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class MergeNiftisOperator(KaapanaBaseOperator):
    def __init__(
        self,
        dag,
        parallel_processes=3,
        overlap_threshold=0.01,
        overlap_strategy="skip",
        log_level="INFO",
        env_vars={},
        execution_timeout=timedelta(minutes=120),
        **kwargs,
    ):
        envs = {
            "LOG_LEVEL": str(log_level),
            "PARALLEL_PROCESSES": str(parallel_processes),
            "OVERLAP_STRATEGY": str(overlap_strategy),
            "OVERLAP_THRESHOLD": str(overlap_threshold),
        }

        env_vars.update(envs)
        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/merge-niftis:{KAAPANA_BUILD_VERSION}",
            name="merge-niftis",
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=10000,
            **kwargs,
        )
