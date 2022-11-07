import os
from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version

class ProcessStudyIdsOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 name='trigger-dcmsend-job-from-doccano',
                 execution_timeout=timedelta(minutes=20),
                 env_vars=None,
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}
        envs = {
            "HOSTDOMAIN": os.getenv('HOSTDOMAIN'),
        }
        env_vars.update(envs)
        super().__init__(
            dag=dag,
            name=name,
            image=f"{default_registry}/doccano-processing:{kaapana_build_version}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            ram_mem_mb=1000,
            ram_mem_mb_lmt=3000,
            *args, **kwargs
        )