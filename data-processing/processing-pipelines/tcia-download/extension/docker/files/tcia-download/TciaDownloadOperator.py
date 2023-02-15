from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version

class TciaDownloadOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 parallel_processes=4,
                 subset=0,
                 execution_timeout=None,
                 env_vars=None,
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "SUBSET": str(subset),
            "PARALLEL_PROCESSES": str(parallel_processes),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name='tcia-download',
            image=f"{default_registry}/tcia-download:{kaapana_build_version}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            ram_mem_mb = int(50 * parallel_processes),
            ram_mem_mb_lmt = int(300 * parallel_processes) if int(300 * parallel_processes) < 16000 else 16000,
            enable_proxy=True,
            *args,
            **kwargs
        )
