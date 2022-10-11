from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_platform_abbr, \
    default_platform_version


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
            image=f"{default_registry}/total-segmentator:{default_platform_abbr}_{default_platform_version}__3.6.4",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            keep_parallel_id=False,
            env_vars=env_vars,
            ram_mem_mb=5000,
            **kwargs
        )
