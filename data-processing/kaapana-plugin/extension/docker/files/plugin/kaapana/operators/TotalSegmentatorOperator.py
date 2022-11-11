from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version


class TotalSegmentatorOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(minutes=10)

    def __init__(self,
                 dag,
                 name="total-segmentator",
                 env_vars={},
                 execution_timeout=execution_timeout,
                 **kwargs
                 ):
        super().__init__(
            dag=dag,
            image=f"{default_registry}/total-segmentator:{kaapana_build_version}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            keep_parallel_id=False,
            env_vars=env_vars,
            ram_mem_mb=16000,
            ram_mem_mb_lmt=45000,
            **kwargs
        )
