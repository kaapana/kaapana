from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project


class GaNDLFFullTestCaseOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 execution_timeout=timedelta(seconds=600),
                 *args, **kwargs
                 ):

        super().__init__(
            dag=dag,
            name='run-full-test-cases',
            image=f"registry.hzdr.de/santhosh.parampottupadam/san-kap/gandlf-workflow:0.0.1",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            enable_proxy=True,
            host_network=True,
            ram_mem_mb=6000,
            *args,
            **kwargs
        )

